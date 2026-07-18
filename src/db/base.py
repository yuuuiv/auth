from typing import Any, Optional

from fastapi import HTTPException, status

from models import User
from config import settings


class MetaDBClient(type):

    cilent_map = {}

    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        if hasattr(cls, '_type'):
            MetaDBClient.cilent_map[cls._type] = cls


class DBClientBase(metaclass=MetaDBClient):

    @staticmethod
    def get_client() -> "DBClientBase":
        if not settings.enabled_db:
            raise HTTPException(
                status_code=400, detail="DB not enabled"
            )
        cls = MetaDBClient.cilent_map.get(settings.db_client_type)
        if cls is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="DB type not supported"
            )
        return cls

    @classmethod
    def login_user(cls, user: User) -> bool:
        return True

    @classmethod
    def register_user(cls, user: User) -> bool:
        return True

    @classmethod
    def update_oauth_user(cls, user: User) -> bool:
        return True

    @classmethod
    def get_user_by_email(cls, email: str) -> Optional[dict[str, Any]]:
        return None

    @classmethod
    def get_user_by_id(cls, user_id: str) -> Optional[dict[str, Any]]:
        return None

    @classmethod
    def register_email_user(cls, email: str, password_hash: str, role: str = "user") -> Optional[dict[str, Any]]:
        return None

    @classmethod
    def update_password(cls, email: str, password_hash: str) -> None:
        return None
