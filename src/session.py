import datetime
import logging
import secrets
from typing import Any

import jwt
from fastapi import HTTPException, Request, status

from config import settings


_logger = logging.getLogger(__name__)


def public_user(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id")),
        "email": row.get("user_email", ""),
        "name": row.get("user_name") or row.get("user_email", ""),
        "role": row.get("role", "user"),
        "active": bool(row.get("active", True)),
    }


def issue_token(row: dict[str, Any]) -> tuple[str, int]:
    if not settings.auth_jwt_secret:
        raise HTTPException(status_code=503, detail="Auth JWT secret is not configured")
    now = datetime.datetime.now(datetime.timezone.utc)
    expires_at = now + datetime.timedelta(days=settings.auth_token_expire_days)
    payload = {
        "iss": settings.auth_issuer,
        "aud": settings.auth_audience,
        "sub": str(row.get("id")),
        "email": row.get("user_email", ""),
        "name": row.get("user_name") or row.get("user_email", ""),
        "role": row.get("role", "user"),
        "jti": secrets.token_urlsafe(18),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.auth_jwt_secret, algorithm="HS256"), int(expires_at.timestamp())


def decode_token(token: str) -> dict[str, Any]:
    if not token or not settings.auth_jwt_secret:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return jwt.decode(
            token,
            settings.auth_jwt_secret,
            algorithms=["HS256"],
            issuer=settings.auth_issuer,
            audience=settings.auth_audience,
            options={"require": ["exp", "iat", "sub", "jti", "iss", "aud"]},
            leeway=30,
        )
    except jwt.PyJWTError as exc:
        _logger.info("Invalid session token: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid session") from exc


def token_from_request(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.cookies.get(settings.auth_cookie_name, "")
