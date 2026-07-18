import jwt
import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import settings
from models import User
from src.temp_mail_bridge import is_configured as temp_mail_bridge_configured

router = APIRouter()
security = HTTPBearer()
_logger = logging.getLogger(__name__)


@router.get("/api/settings", tags=["Auth"])
def auth_settings():
    central_session_ready = bool(settings.enabled_db and settings.auth_jwt_secret)
    return {
        "enabled_smtp": settings.enabled_db and settings.enabled_smtp,
        "enabled_github": central_session_ready and bool(settings.github_client_id and settings.github_client_secret),
        "enabled_google": central_session_ready and bool(settings.google_client_id and settings.google_client_secret),
        "enabled_ms": central_session_ready and bool(settings.ms_client_id and settings.ms_client_secret),
        "enabled_web3": settings.enabled_web3_client,
        "cf_turnstile_site_key": settings.cf_turnstile_site_key,
        "temp_mail_bridge_enabled": temp_mail_bridge_configured(),
    }


@router.get("/api/info", tags=["User"])
def info(app_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    if app_id not in settings.app_settings:
        raise HTTPException(
            status_code=400, detail="App ID not found"
        )
    app_settings = settings.app_settings[app_id]
    try:
        jwt_token = credentials.credentials
        payload = jwt.decode(
            jwt_token, app_settings.app_secret, algorithms=["HS256"])
        user = User.model_validate(payload)
        if user.expire_at < datetime.datetime.now().timestamp():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        return user
    except Exception as e:
        _logger.error(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalid")
