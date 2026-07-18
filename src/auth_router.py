import jwt
import uuid
import datetime
import logging
import secrets
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from config import settings
from models import OauthBody, TokenBody
from src.auth import AuthClientBase
from src.db.base import DBClientBase
from src.cache.base import TokenClientBase
from src.temp_mail_bridge import try_sync_temp_mail_user

router = APIRouter()
_logger = logging.getLogger(__name__)
_STATEFUL_PROVIDERS = {"github", "google"}


def _oauth_provider_configured(login_type: str) -> bool:
    credentials = {
        "github": (settings.github_client_id, settings.github_client_secret),
        "google": (settings.google_client_id, settings.google_client_secret),
        "ms": (settings.ms_client_id, settings.ms_client_secret),
    }
    provider_credentials = credentials.get(login_type)
    if provider_credentials is None:
        return True
    return bool(
        settings.enabled_db
        and settings.auth_jwt_secret
        and all(provider_credentials)
    )


def _validate_redirect_url(redirect_url: str) -> None:
    if not redirect_url:
        return
    parsed = urlparse(redirect_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if parsed.scheme not in {"http", "https"} or origin not in settings.get_cors_allow_origins():
        raise HTTPException(status_code=400, detail="OAuth redirect URL is not allowed")


def _oauth_state_cookie_name(login_type: str) -> str:
    return f"{settings.auth_cookie_name}_oauth_{login_type}"


def _oauth_return_cookie_name(login_type: str) -> str:
    return f"{settings.auth_cookie_name}_oauth_return_{login_type}"


def _cookie_domain_for_request(request: Request) -> str | None:
    configured = settings.auth_cookie_domain.strip()
    hostname = (request.url.hostname or "").lower().rstrip(".")
    cookie_root = configured.lower().lstrip(".").rstrip(".")
    if configured and (hostname == cookie_root or hostname.endswith(f".{cookie_root}")):
        return configured
    return None


def _prepare_login(
    request: Request,
    response: Response,
    login_type: str,
    redirect_url: str = "",
    return_to: str = "",
) -> str:
    client = AuthClientBase.get_client(login_type)
    if not _oauth_provider_configured(login_type):
        raise HTTPException(status_code=503, detail=f"{login_type} OAuth is not configured")
    _validate_redirect_url(redirect_url)
    _validate_redirect_url(return_to)
    if login_type not in _STATEFUL_PROVIDERS:
        return client.get_login_url(redirect_url)

    state = secrets.token_urlsafe(32)
    cookie_options = {
        "key": _oauth_state_cookie_name(login_type),
        "value": state,
        "max_age": 600,
        "httponly": True,
        "secure": not settings.debug,
        "samesite": "lax",
        "path": "/api/session/oauth-callback",
    }
    cookie_domain = _cookie_domain_for_request(request)
    if cookie_domain:
        cookie_options["domain"] = cookie_domain
    response.set_cookie(**cookie_options)
    if return_to:
        return_cookie_options = {
            **cookie_options,
            "key": _oauth_return_cookie_name(login_type),
            "value": return_to,
        }
        response.set_cookie(**return_cookie_options)
    return client.get_login_url(redirect_url, state)


@router.get("/api/login", tags=["Auth"])
def login(
    request: Request,
    response: Response,
    login_type: str,
    redirect_url: str = "",
    return_to: str = "",
):
    return _prepare_login(request, response, login_type, redirect_url, return_to)


@router.get("/api/login/redirect", tags=["Auth"])
def login_redirect(
    request: Request,
    login_type: str,
    redirect_url: str = "",
    return_to: str = "",
):
    response = RedirectResponse(url="/", status_code=302)
    login_url = _prepare_login(request, response, login_type, redirect_url, return_to)
    response.headers["location"] = login_url
    return response


@router.post("/api/oauth", tags=["Auth"])
def oauth(oauth_body: OauthBody):
    client = AuthClientBase.get_client(oauth_body.login_type)
    if oauth_body.app_id not in settings.app_settings:
        raise HTTPException(
            status_code=400, detail="App ID not found"
        )
    app_settings = settings.app_settings[oauth_body.app_id]
    try:
        user = client.get_user(oauth_body)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Can't get user info: {e}"
        )
    if not user:
        raise HTTPException(
            status_code=400, detail="Can't get user info"
        )
    user.expire_at = (
        datetime.datetime.now() +
        datetime.timedelta(days=app_settings.token_expire_days)
    ).timestamp()
    jwt_value = jwt.encode(
        user.model_dump(),
        app_settings.app_secret,
        algorithm="HS256"
    )
    token_client = TokenClientBase.get_client()
    code = uuid.uuid4().hex
    token_client.store_token(f"{app_settings.app_id}:{code}", jwt_value, settings.token_code_expire_seconds)
    # update user info to db if enabled
    if settings.enabled_db:
        db_client = DBClientBase.get_client()
        db_client.update_oauth_user(user)
    try_sync_temp_mail_user(user.user_email or user.user_name)
    return {
        "redirect_url": app_settings.redirect_url,
        "code": code
    }


@router.post("/api/token", tags=["Auth"])
def token(token_body: TokenBody):
    token_client = TokenClientBase.get_client()
    if not token_client:
        raise HTTPException(
            status_code=400, detail="Token client not found"
        )
    jwt_value = token_client.get_token(f"{token_body.app_id}:{token_body.code}")
    if not jwt_value:
        raise HTTPException(
            status_code=400, detail="Token not found or expired"
        )
    return {
        "jwt": jwt_value
    }
