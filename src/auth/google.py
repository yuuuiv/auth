import requests
import logging
from urllib.parse import urlencode

from typing import Optional

from models import OauthBody, User

from src.auth.base import AuthClientBase
from config import settings

_logger = logging.getLogger(__name__)

GOOGLE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOEKN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL = "https://www.googleapis.com/oauth2/v1/userinfo"
REQUEST_TIMEOUT_SECONDS = 10


class GoogleAuthClient(AuthClientBase):

    _login_type = "google"

    @classmethod
    def get_login_url(cls, redirect_url: str = "", state: str = "") -> str:
        params = {
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile",
            "client_id": settings.google_client_id,
            "redirect_uri": redirect_url,
            "access_type": "online",
            "prompt": "select_account",
        }
        if state:
            params["state"] = state
        return f"{GOOGLE_URL}?{urlencode(params)}"

    @classmethod
    def get_user(cls, oauth_body: OauthBody) -> Optional[User]:
        if not oauth_body.code:
            return None
        token_response = requests.post(
            GOOGLE_TOEKN_URL,
            data={
                'code': oauth_body.code,
                'client_id': settings.google_client_id,
                'redirect_uri': oauth_body.redirect_url,
                'client_secret': settings.google_client_secret,
                'grant_type': 'authorization_code'
            },
            headers={"Accept": "application/json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        token_response.raise_for_status()
        token_res = token_response.json()
        if not token_res.get('access_token'):
            raise ValueError("Can't get access token from google")
        access_token = token_res['access_token']
        user_response = requests.get(
            GOOGLE_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        user_response.raise_for_status()
        res = user_response.json()
        origin_data = res
        user_email = res.get('email')
        if not user_email or res.get("verified_email") is not True:
            raise ValueError("Google account email is missing or unverified")
        user_name = user_email.replace("@gmail.com", "")
        return User(
            login_type=cls._login_type,
            user_name=user_name,
            user_email=user_email,
            origin_data=origin_data
        )
