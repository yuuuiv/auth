import logging
import secrets
from typing import Any, Optional
from datetime import datetime, timezone

import requests

from config import settings
from models import User
from src.passwords import hash_password, verify_password

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
        stored_password = data[0].get("password", "")
        if not verify_password(stored_password, user.password):
            raise HTTPException(
                status_code=400, detail="User password incorrect"
            )
        if stored_password and not stored_password.startswith("scrypt$"):
            cls.update_password(user.user_email, hash_password(user.password))
        return True

    @classmethod
    def register_user(cls, user: User) -> bool:
        res = requests.post(
            f"{cls._rest_base_url()}/awsl_users",
            params={"on_conflict": "user_email"},
            json={
                "user_name": user.user_name,
                "user_email": user.user_email,
                "password": user.password if user.password.startswith("scrypt$") else hash_password(user.password),
                "updated_at": cls._updated_at(),
            },
            headers=cls._headers("resolution=merge-duplicates,return=minimal"),
        )
        if res.status_code >= 400:
            cls._raise_supabase_error("Failed to register user", res)
        return True

    @classmethod
    def get_user_by_email(cls, email: str) -> Optional[dict[str, Any]]:
        res = requests.get(
            f"{cls._rest_base_url()}/awsl_users",
            params={
                "user_email": f"eq.{email}",
                "select": "id,user_name,user_email,password,active,role",
                "limit": "1",
            },
            headers=cls._headers(),
        )
        if res.status_code >= 400:
            cls._raise_supabase_error("Failed to find user", res)
        data = res.json()
        return data[0] if data else None

    @classmethod
    def get_user_by_id(cls, user_id: str) -> Optional[dict[str, Any]]:
        res = requests.get(
            f"{cls._rest_base_url()}/awsl_users",
            params={
                "id": f"eq.{user_id}",
                "select": "id,user_name,user_email,password,active,role",
                "limit": "1",
            },
            headers=cls._headers(),
        )
        if res.status_code >= 400:
            cls._raise_supabase_error("Failed to find user", res)
        data = res.json()
        return data[0] if data else None

    @classmethod
    def register_email_user(cls, email: str, password_hash: str, role: str = "user") -> Optional[dict[str, Any]]:
        res = requests.post(
            f"{cls._rest_base_url()}/awsl_users",
            params={"on_conflict": "user_email"},
            json=[{
                "user_name": email,
                "user_email": email,
                "password": password_hash,
                "role": role,
                "updated_at": cls._updated_at(),
            }],
            headers=cls._headers("resolution=merge-duplicates,return=representation"),
        )
        if res.status_code >= 400:
            cls._raise_supabase_error("Failed to register user", res)
        data = res.json()
        return data[0] if data else cls.get_user_by_email(email)

    @classmethod
    def update_password(cls, email: str, password_hash: str) -> None:
        res = requests.patch(
            f"{cls._rest_base_url()}/awsl_users",
            params={"user_email": f"eq.{email}"},
            json={"password": password_hash, "updated_at": cls._updated_at()},
            headers=cls._headers("return=minimal"),
        )
        if res.status_code >= 400:
            cls._raise_supabase_error("Failed to update password", res)

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
