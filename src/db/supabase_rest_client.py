import logging
import secrets
from datetime import datetime, timezone

import requests

from config import settings
from models import User

from .base import DBClientBase
from fastapi import HTTPException


_logger = logging.getLogger(__name__)


class SupabaseRestClient(DBClientBase):

    _type = "supabase_rest"

    @staticmethod
    def _rest_base_url() -> str:
        base = settings.supabase_api_url.rstrip("/")
        if base.endswith("/rest/v1"):
            return base
        return f"{base}/rest/v1"

    @staticmethod
    def _updated_at() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _headers(prefer: str = "") -> dict[str, str]:
        headers = {
            "apikey": settings.supabase_api_key,
            "Authorization": f"Bearer {settings.supabase_api_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    @staticmethod
    def _error_detail(res: requests.Response) -> str:
        try:
            body = res.json()
        except ValueError:
            return res.text or res.reason

        if isinstance(body, dict):
            parts = [
                str(body[key])
                for key in ("message", "details", "hint", "code")
                if body.get(key)
            ]
            return " | ".join(parts) if parts else str(body)
        return str(body)

    @classmethod
    def _raise_supabase_error(cls, action: str, res: requests.Response) -> None:
        detail = cls._error_detail(res)
        _logger.error("%s: %s %s", action, res.status_code, detail)
        raise HTTPException(
            status_code=400,
            detail=f"{action}: {res.status_code} {detail}"
        )

    @classmethod
    def login_user(cls, user: User) -> bool:
        res = requests.get(
            f"{cls._rest_base_url()}/awsl_users",
            params={"user_email": f"eq.{user.user_email}", "select": "password"},
            headers=cls._headers(),
        )
        if res.status_code >= 400:
            cls._raise_supabase_error("Failed to login user", res)
        try:
            data = res.json()
        except Exception as e:
            _logger.error(f"Failed to parse user data: {e}")
            raise HTTPException(
                status_code=400, detail=f"Failed to parse user data: {e}"
            )
        if len(data) == 0:
            raise HTTPException(
                status_code=400, detail="User not found"
            )
        if not secrets.compare_digest(data[0].get("password", ""), user.password):
            raise HTTPException(
                status_code=400, detail="User password incorrect"
            )
        return True

    @classmethod
    def register_user(cls, user: User) -> bool:
        res = requests.post(
            f"{cls._rest_base_url()}/awsl_users",
            params={"on_conflict": "user_email"},
            json={
                "user_name": user.user_name,
                "user_email": user.user_email,
                "password": user.password,
                "updated_at": cls._updated_at(),
            },
            headers=cls._headers("resolution=merge-duplicates,return=minimal"),
        )
        if res.status_code >= 400:
            cls._raise_supabase_error("Failed to register user", res)
        return True

    @classmethod
    def update_oauth_user(cls, user: User) -> bool:
        res = requests.post(
            f"{cls._rest_base_url()}/awsl_oauth_users",
            params={"on_conflict": "login_type,user_email"},
            json={
                "login_type": user.login_type,
                "user_name": user.user_name,
                "user_email": user.user_email,
                "web3_account": user.web3_account,
                "origin_data": user.origin_data,
                "updated_at": cls._updated_at(),
            },
            headers=cls._headers("resolution=merge-duplicates,return=minimal"),
        )
        if res.status_code >= 400:
            cls._raise_supabase_error("Failed to update user", res)
        return True
