import re
import uuid
import secrets
import logging

from fastapi import APIRouter, HTTPException, Request

from config import settings
from models import EmailUser, User
from src.auth.email import MailAuthClient
from src.cf_turnstile import CloudFlareTurnstile
from src.db.base import DBClientBase
from src.email.base import MailClientBase
from src.cache.base import TokenClientBase
from src.temp_mail_bridge import try_sync_temp_mail_user

router = APIRouter()
_logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$", re.IGNORECASE)


def normalize_email(value: str) -> str:
    return value.strip().lower()


@router.post("/api/email/login", tags=["Email"])
def login(email_user: EmailUser, request: Request):
    email = normalize_email(email_user.email)
    if not EMAIL_REGEX.fullmatch(email) or not email_user.password:
        raise HTTPException(status_code=400, detail="Invalid email or password")
    token_client = TokenClientBase.get_client()
    token_client.check_rate_limit(
        f"login:legacy:email:{email}",
        settings.login_rate_limit_timewindow_seconds,
        settings.login_rate_limit_max_requests,
    )
    token_client.check_rate_limit(
        f"login:legacy:ip:{get_real_ipaddr(request)}",
        settings.login_rate_limit_timewindow_seconds,
        settings.login_rate_limit_max_requests,
    )
    db_client = DBClientBase.get_client()
    db_client.login_user(User(
        login_type=MailAuthClient._login_type,
        user_name=email,
        user_email=email,
        password=email_user.password,
    ))
    try_sync_temp_mail_user(email, email_user.password)
    code = uuid.uuid4().hex
    token_client.store_token(f"email_login:{code}", email, settings.token_code_expire_seconds)
    return {
        "code": code
    }


def get_real_ipaddr(request: Request) -> str:
    if "x-real-ip" in request.headers:
        return request.headers["x-real-ip"]
    else:
        if not request.client or not request.client.host:
            return "127.0.0.1"

        return request.client.host


@router.post("/api/email/verify_code", tags=["Email"])
def verify_code(email_user: EmailUser, request: Request):
    email = normalize_email(email_user.email)
    if not EMAIL_REGEX.fullmatch(email):
        raise HTTPException(
            status_code=400, detail="Invalid email"
        )
    remote_ip = get_real_ipaddr(request)
    CloudFlareTurnstile.check(email_user.cf_token, remote_ip)
    _logger.info(f"remote_ip={remote_ip}, Verify code for {email}")
    token_client = TokenClientBase.get_client()
    mail_client = MailClientBase.get_client()
    token_client.check_rate_limit(
        f"email_rate_limit:legacy:email:{email}", settings.email_rate_limit_timewindow_seconds,
        settings.email_rate_limit_max_requests
    )
    token_client.check_rate_limit(
        f"email_rate_limit:legacy:ip:{remote_ip}", settings.email_rate_limit_timewindow_seconds,
        settings.email_rate_limit_max_requests
    )
    res = token_client.get_token(f"email_verify_code:{email}")
    if res:
        raise HTTPException(
            status_code=400, detail=f"Verify code already sent, Validity period {settings.verify_code_expire_seconds} seconds"
        )
    code = f"{secrets.randbelow(1_000_000):06d}"
    token_client.store_token(f"email_verify_code:{email}", code, settings.verify_code_expire_seconds)
    # skip sending email in debug mode
    if settings.debug:
        _logger.info(f"Send verify code to {email}: {code}")
    else:
        mail_client.send_verify_code(email, code)
    return {
        "timeout": settings.verify_code_expire_seconds,
    }


@router.post("/api/email/register", tags=["Email"])
def register(email_user: EmailUser):
    email = normalize_email(email_user.email)
    if not all([
            email,
            EMAIL_REGEX.fullmatch(email),
            email_user.password,
            email_user.code
    ]):
        raise HTTPException(
            status_code=400, detail="Invalid email user"
        )
    db_client = DBClientBase.get_client()
    token_client = TokenClientBase.get_client()
    token_client.check_rate_limit(
        f"email_verify_attempt:legacy:{email}",
        settings.verification_attempt_timewindow_seconds,
        settings.verification_attempt_max_requests,
    )
    res = token_client.get_token(f"email_verify_code:{email}")
    if not res:
        raise HTTPException(
            status_code=400, detail="Can't get verify code"
        )
    if not secrets.compare_digest(str(res), email_user.code):
        raise HTTPException(
            status_code=400, detail="Verify code not match"
        )
    db_client.register_user(User(
        login_type=MailAuthClient._login_type,
        user_name=email,
        user_email=email,
        password=email_user.password,
    ))
    token_client.store_token(f"email_verify_code:{email}", "", 1)
    try_sync_temp_mail_user(email, email_user.password)
    return {
        "status": "OK"
    }
