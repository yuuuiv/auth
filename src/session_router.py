import logging
import re
import secrets
import time

import jwt

from fastapi import APIRouter, HTTPException, Request, Response

from config import settings
from models import (
    OauthBody,
    SessionExchangeBody,
    SessionLoginBody,
    SessionOAuthCallbackBody,
    SessionRegisterBody,
    SessionVerifyCodeBody,
)
from src.auth import AuthClientBase
from src.cache.base import TokenClientBase
from src.cf_turnstile import CloudFlareTurnstile
from src.db.base import DBClientBase
from src.email.base import MailClientBase
from src.passwords import hash_password, is_legacy_hash, verify_password
from src.session import decode_token, issue_token, public_user, token_from_request


router = APIRouter(prefix="/api/session", tags=["Session"])
_logger = logging.getLogger(__name__)
_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _email(value: str) -> str:
    normalized = value.strip().lower()
    if not _EMAIL_REGEX.match(normalized):
        raise HTTPException(status_code=400, detail="Invalid email")
    return normalized


def _db():
    if not settings.enabled_db:
        raise HTTPException(status_code=503, detail="Auth database is not configured")
    return DBClientBase.get_client()


def _set_cookie(response: Response, token: str, max_age: int) -> None:
    options = {
        "key": settings.auth_cookie_name,
        "value": token,
        "max_age": max_age,
        "httponly": True,
        "secure": not settings.debug,
        "samesite": "lax",
        "path": "/",
    }
    if settings.auth_cookie_domain:
        options["domain"] = settings.auth_cookie_domain
    response.set_cookie(**options)


def _row_with_admin_role(row: dict) -> dict:
    if row.get("user_email", "").lower() in settings.get_admin_emails():
        row = dict(row)
        row["role"] = "admin"
    return row


@router.get("/me")
def session_me(request: Request):
    claims = decode_token(token_from_request(request))
    db = _db()
    row = db.get_user_by_id(str(claims.get("sub", "")))
    if not row or not row.get("active", True):
        raise HTTPException(status_code=401, detail="Account is inactive")
    return {"user": public_user(_row_with_admin_role(row))}


@router.post("/login")
def session_login(body: SessionLoginBody, request: Request, response: Response):
    email = _email(body.email)
    if not body.password:
        raise HTTPException(status_code=400, detail="Password is required")
    db = _db()
    row = db.get_user_by_email(email)
    if not row or not row.get("active", True) or not verify_password(row.get("password", ""), body.password):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    if is_legacy_hash(row.get("password", "")):
        db.update_password(email, hash_password(body.password))
        row = db.get_user_by_email(email) or row
    row = _row_with_admin_role(row)
    token, expires_at = issue_token(row)
    _set_cookie(response, token, max(0, expires_at - int(time.time())))
    return {"user": public_user(row), "access_token": token, "expires_at": expires_at}


@router.post("/verify-code")
def session_verify_code(body: SessionVerifyCodeBody, request: Request):
    email = _email(body.email)
    if settings.cf_turnstile_secret_key:
        client_ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "127.0.0.1")
        CloudFlareTurnstile.check(body.cf_token, client_ip)
    token_client = TokenClientBase.get_client()
    existing = token_client.get_token(f"email_verify_code:{email}")
    if existing:
        raise HTTPException(status_code=400, detail="Verify code already sent")
    if not settings.enabled_smtp:
        raise HTTPException(status_code=503, detail="Email registration is disabled")
    token_client.check_rate_limit(
        f"email_rate_limit:{email}",
        settings.email_rate_limit_timewindow_seconds,
        settings.email_rate_limit_max_requests,
    )
    import random
    import string
    code = "".join(random.choices(string.digits, k=6))
    token_client.store_token(f"email_verify_code:{email}", code, settings.verify_code_expire_seconds)
    if settings.debug:
        _logger.info("Verification code generated for %s: %s", email, code)
    else:
        MailClientBase.get_client().send_verify_code(email, code)
    return {"timeout": settings.verify_code_expire_seconds}


@router.post("/register")
def session_register(body: SessionRegisterBody, request: Request, response: Response):
    email = _email(body.email)
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must contain at least 8 characters")
    token_client = TokenClientBase.get_client()
    expected_code = token_client.get_token(f"email_verify_code:{email}")
    if not settings.debug and (not expected_code or not body.code or expected_code != body.code):
        raise HTTPException(status_code=400, detail="Verify code is invalid or expired")
    db = _db()
    if db.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="Account already exists")
    role = "admin" if email in settings.get_admin_emails() else "user"
    row = db.register_email_user(email, hash_password(body.password), role) or db.get_user_by_email(email)
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create account")
    token_client.store_token(f"email_verify_code:{email}", "", 1)
    row = _row_with_admin_role(row)
    token, expires_at = issue_token(row)
    _set_cookie(response, token, max(0, expires_at - int(time.time())))
    return {"user": public_user(row), "access_token": token, "expires_at": expires_at}


@router.post("/oauth-exchange")
def session_oauth_exchange(body: SessionExchangeBody, response: Response):
    """Exchange the legacy provider code for a central auth session.

    The application never receives or sends the configured app secret. This
    keeps the existing provider adapters usable while making the final
    session consumed by neofantasy-api a central auth JWT.
    """
    app_settings = settings.app_settings.get(body.app_id)
    if not app_settings:
        raise HTTPException(status_code=400, detail="App ID not found")
    token_client = TokenClientBase.get_client()
    legacy_token = token_client.get_token(f"{body.app_id}:{body.code}")
    if not legacy_token:
        raise HTTPException(status_code=400, detail="OAuth code not found or expired")
    try:
        legacy_user = jwt.decode(legacy_token, app_settings.app_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid OAuth code") from exc
    token_client.store_token(f"{body.app_id}:{body.code}", "", 1)
    email = _email(legacy_user.get("user_email") or legacy_user.get("user_name") or "")
    db = _db()
    row = db.get_user_by_email(email)
    if not row:
        role = "admin" if email in settings.get_admin_emails() else "user"
        row = db.register_email_user(email, hash_password(secrets.token_urlsafe(32)), role)
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create OAuth identity")
    row = _row_with_admin_role(row)
    token, expires_at = issue_token(row)
    _set_cookie(response, token, max(0, expires_at - int(time.time())))
    return {"user": public_user(row), "access_token": token, "expires_at": expires_at}


@router.post("/oauth-callback")
def session_oauth_callback(body: SessionOAuthCallbackBody, request: Request, response: Response):
    """Complete a first-party Google/GitHub login and issue the central session."""
    if not body.code:
        raise HTTPException(status_code=400, detail="OAuth code is required")
    if body.login_type in {"google", "github"}:
        state_cookie_name = f"{settings.auth_cookie_name}_oauth_{body.login_type}"
        expected_state = request.cookies.get(state_cookie_name, "")
        response.delete_cookie(
            state_cookie_name,
            domain=settings.auth_cookie_domain or None,
            path="/api/session/oauth-callback",
        )
        if not expected_state or not body.state or not secrets.compare_digest(expected_state, body.state):
            raise HTTPException(status_code=400, detail="OAuth state is invalid or expired")
    client = AuthClientBase.get_client(body.login_type)
    try:
        user = client.get_user(OauthBody(
            app_id="neofantasy-live",
            login_type=body.login_type,
            code=body.code,
            redirect_url=body.redirect_url,
            web3_account=body.web3_account or None,
        ))
    except Exception as exc:
        _logger.warning("OAuth callback failed for %s: %s", body.login_type, exc)
        raise HTTPException(status_code=401, detail="OAuth login failed") from exc
    if not user:
        raise HTTPException(status_code=401, detail="OAuth identity not found")

    email = _email(user.user_email or user.user_name or "")
    db = _db()
    row = db.get_user_by_email(email)
    if row and not row.get("active", True):
        raise HTTPException(status_code=403, detail="Account is inactive")
    if not row:
        role = "admin" if email in settings.get_admin_emails() else "user"
        row = db.register_email_user(email, hash_password(secrets.token_urlsafe(32)), role)
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create OAuth identity")
    try:
        db.update_oauth_user(user)
    except Exception as exc:
        # The central account remains the source of truth. Keep login available
        # while reporting a missing/legacy OAuth audit table for migration.
        _logger.warning("OAuth identity history could not be saved for %s: %s", body.login_type, exc)
    row = _row_with_admin_role(row)
    token, expires_at = issue_token(row)
    _set_cookie(response, token, max(0, expires_at - int(time.time())))
    return {"user": public_user(row), "access_token": token, "expires_at": expires_at}


@router.post("/logout")
def session_logout(response: Response):
    response.delete_cookie(settings.auth_cookie_name, domain=settings.auth_cookie_domain or None, path="/")
    return {"ok": True}
