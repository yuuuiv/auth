import datetime
import logging

import jwt
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import settings
from models import User
from src.temp_mail_bridge import (
    bind_verified_address_jwt,
    create_bound_address,
    delete_address_mail,
    get_address_jwt,
    get_address_forwarding_rules,
    get_bound_addresses,
    list_user_mails,
    list_user_sendbox,
    save_address_forwarding_rules,
    sync_temp_mail_user,
)


router = APIRouter()
security = HTTPBearer()
_logger = logging.getLogger(__name__)


def current_user(
    app_id: str = Query(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    if app_id not in settings.app_settings:
        raise HTTPException(status_code=400, detail="App ID not found")
    app_settings = settings.app_settings[app_id]
    try:
        payload = jwt.decode(
            credentials.credentials,
            app_settings.app_secret,
            algorithms=["HS256"],
        )
        user = User.model_validate(payload)
        if user.expire_at < datetime.datetime.now().timestamp():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )
        if not (user.user_email or user.user_name):
            raise HTTPException(status_code=400, detail="User email not found")
        return user
    except HTTPException:
        raise
    except Exception as exc:
        _logger.error("Invalid auth token for temp-mail bridge: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid",
        ) from exc


def user_email(user: User) -> str:
    return user.user_email or user.user_name


@router.post("/api/temp-mail/sync_user", tags=["Temp Mail"])
def sync_user(user: User = Depends(current_user)):
    row = sync_temp_mail_user(user_email(user))
    return {
        "success": True,
        "user": row,
    }


@router.get("/api/temp-mail/addresses", tags=["Temp Mail"])
def addresses(user: User = Depends(current_user)):
    row, results = get_bound_addresses(user_email(user))
    return {
        "user": row,
        "count": len(results),
        "results": results,
    }


@router.get("/api/temp-mail/address_jwt/{address_id}", tags=["Temp Mail"])
def address_jwt(address_id: int, user: User = Depends(current_user)):
    return get_address_jwt(user_email(user), address_id)


@router.get("/api/temp-mail/address_forwarding_rules/{address_id}", tags=["Temp Mail"])
def address_forwarding_rules(address_id: int, user: User = Depends(current_user)):
    return get_address_forwarding_rules(user_email(user), address_id)


@router.post("/api/temp-mail/address_forwarding_rules/{address_id}", tags=["Temp Mail"])
def save_address_rules(address_id: int, payload: dict = Body(default={}), user: User = Depends(current_user)):
    rules = payload.get("rules")
    if not isinstance(rules, list):
        raise HTTPException(status_code=400, detail="rules 必须是数组")
    return save_address_forwarding_rules(user_email(user), address_id, rules)


@router.delete("/api/temp-mail/address_mail/{address_id}/{mail_id}", tags=["Temp Mail"])
def delete_mail(address_id: int, mail_id: int, user: User = Depends(current_user)):
    return delete_address_mail(user_email(user), address_id, mail_id)


@router.post("/api/temp-mail/new_address", tags=["Temp Mail"])
def new_address(payload: dict = Body(default={}), user: User = Depends(current_user)):
    return create_bound_address(user_email(user), payload)


@router.post("/api/temp-mail/bind_address", tags=["Temp Mail"])
def bind_address(payload: dict = Body(default={}), user: User = Depends(current_user)):
    address_jwt = payload.get("jwt") or payload.get("credential")
    if not address_jwt:
        raise HTTPException(status_code=400, detail="缺少地址凭证 JWT")
    return bind_verified_address_jwt(user_email(user), address_jwt)


@router.get("/api/temp-mail/mails", tags=["Temp Mail"])
def mails(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    address: str = "",
    user: User = Depends(current_user),
):
    return list_user_mails(user_email(user), limit, offset, address)


@router.get("/api/temp-mail/sendbox", tags=["Temp Mail"])
def sendbox(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    address: str = "",
    user: User = Depends(current_user),
):
    return list_user_sendbox(user_email(user), limit, offset, address)
