import json
import logging
from typing import Any, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config import settings
from models import User
from src.passwords import hash_password, verify_password

from .base import DBClientBase
from fastapi import HTTPException


_logger = logging.getLogger(__name__)


class SqliteClient(DBClientBase):

    _type = "sqlite"

    sessionmaker = None

    @classmethod
    def init_db_client(cls):
        if cls.sessionmaker is None:
            engine = create_engine(settings.sqlite_db_url)
            tmp_sessionmaker = sessionmaker(bind=engine)
            # create table if not exists
            with tmp_sessionmaker() as session, open("db/sqlite3.sql") as f:
                for exec_sql in f.read().split(";"):
                    if exec_sql.strip():
                        session.execute(text(exec_sql))
            cls.sessionmaker = tmp_sessionmaker

    @classmethod
    def login_user(cls, user: User) -> bool:
        password_in_db = None
        try:
            cls.init_db_client()
            exex_sql = text(
                "SELECT password FROM awsl_users WHERE user_email = :user_email"
            )
            with cls.sessionmaker() as session:
                res = session.execute(
                    exex_sql.bindparams(user_email=user.user_email)
                )
                password_in_db = res.fetchone()
        except Exception as e:
            _logger.error(f"Failed to query user: {e}")
            raise HTTPException(
                status_code=400, detail=f"Failed to query user: {e}"
            )
        if not password_in_db:
            raise HTTPException(
                status_code=400, detail="User not found"
            )
        if not verify_password(password_in_db[0], user.password):
            raise HTTPException(
                status_code=400, detail="User password incorrect"
            )
        if password_in_db[0] and not password_in_db[0].startswith("scrypt$"):
            cls.update_password(user.user_email, hash_password(user.password))
        return True

    @classmethod
    def register_user(cls, user: User) -> bool:
        try:
            cls.init_db_client()
            exec_sql = text(
                "INSERT INTO awsl_users (user_name, user_email, password, updated_at)"
                " VALUES (:user_name, :user_email, :password, datetime('now'))"
                " ON CONFLICT (user_email) DO UPDATE"
                " SET user_name = :user_name, password = :password, updated_at = datetime('now')"
            )
            with cls.sessionmaker() as session:
                session.execute(exec_sql.bindparams(
                    user_name=user.user_name,
                    user_email=user.user_email,
                    password=user.password if user.password.startswith("scrypt$") else hash_password(user.password)
                ))
                session.commit()
        except Exception as e:
            _logger.error(f"Failed to register user: {e}")
            raise HTTPException(
                status_code=400, detail=f"Failed to register user: {e}"
            )
        return True

    @classmethod
    def get_user_by_email(cls, email: str) -> Optional[dict[str, Any]]:
        cls.init_db_client()
        with cls.sessionmaker() as session:
            row = session.execute(text(
                "SELECT id, user_name, user_email, password, active, role "
                "FROM awsl_users WHERE user_email = :email LIMIT 1"
            ), {"email": email}).mappings().first()
            return dict(row) if row else None

    @classmethod
    def get_user_by_id(cls, user_id: str) -> Optional[dict[str, Any]]:
        cls.init_db_client()
        with cls.sessionmaker() as session:
            row = session.execute(text(
                "SELECT id, user_name, user_email, password, active, role "
                "FROM awsl_users WHERE id = :user_id LIMIT 1"
            ), {"user_id": user_id}).mappings().first()
            return dict(row) if row else None

    @classmethod
    def register_email_user(cls, email: str, password_hash: str, role: str = "user") -> Optional[dict[str, Any]]:
        cls.init_db_client()
        with cls.sessionmaker() as session:
            session.execute(text(
                "INSERT INTO awsl_users (user_name, user_email, password, role, updated_at) "
                "VALUES (:email, :email, :password, :role, datetime('now')) "
                "ON CONFLICT (user_email) DO UPDATE SET password=:password, role=:role, updated_at=datetime('now')"
            ), {"email": email, "password": password_hash, "role": role})
            session.commit()
        return cls.get_user_by_email(email)

    @classmethod
    def update_password(cls, email: str, password_hash: str) -> None:
        cls.init_db_client()
        with cls.sessionmaker() as session:
            session.execute(text(
                "UPDATE awsl_users SET password=:password, updated_at=datetime('now') WHERE user_email=:email"
            ), {"email": email, "password": password_hash})
            session.commit()

    @classmethod
    def update_oauth_user(cls, user: User) -> bool:
        try:
            cls.init_db_client()
            exex_sql = text(
                "INSERT INTO awsl_oauth_users"
                " (login_type, user_name, user_email, web3_account, origin_data, updated_at)"
                " VALUES (:login_type, :user_name, :user_email, :web3_account, :origin_data, datetime('now'))"
                " ON CONFLICT (login_type, user_email) DO UPDATE"
                " SET user_name = :user_name, web3_account = :web3_account,"
                " origin_data = :origin_data, updated_at = datetime('now')"
            )
            with cls.sessionmaker() as session:
                session.execute(exex_sql.bindparams(
                    login_type=user.login_type,
                    user_name=user.user_name,
                    user_email=user.user_email,
                    web3_account=user.web3_account,
                    origin_data=json.dumps(user.origin_data)
                ))
                session.commit()
        except Exception as e:
            _logger.error(f"Failed to update user: {e}")
            raise HTTPException(
                status_code=400, detail=f"Failed to update user: {e}"
            )
        return True
