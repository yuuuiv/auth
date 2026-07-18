import requests
import logging
from urllib.parse import urlencode

from typing import Optional

from models import OauthBody, User

from src.auth.base import AuthClientBase
from config import settings

_logger = logging.getLogger(__name__)

GITHUB_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAIL_URL = "https://api.github.com/user/emails"
REQUEST_TIMEOUT_SECONDS = 10


class GithubAuthClient(AuthClientBase):

    _login_type = "github"

    @classmethod
    def get_login_url(cls, redirect_url: str = "", state: str = "") -> str:
        params = {
            "client_id": settings.github_client_id,
            "scope": "user:email",
        }
        if redirect_url:
            params["redirect_uri"] = redirect_url
        if state:
            params["state"] = state
        return f"{GITHUB_URL}?{urlencode(params)}"

    @classmethod
    def get_user(cls, oauth_body: OauthBody) -> Optional[User]:
        if not oauth_body.code:
            return None
        token_response = requests.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": oauth_body.code,
                "redirect_uri": oauth_body.redirect_url or None,
            },
            headers={"Accept": "application/json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        token_response.raise_for_status()
        token_res = token_response.json()
        if not token_res.get('access_token'):
            raise ValueError("Can't get access token from github")
        access_token = token_res['access_token']
        user_response = requests.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        user_response.raise_for_status()
        res = user_response.json()
        user_name = res.get('login')
        origin_data = res

        if not user_name:
            raise ValueError("Can't get user name from github")

        email_response = requests.get(
            GITHUB_EMAIL_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        email_response.raise_for_status()
        verified_emails = [
            email
            for email in email_response.json()
            if email.get("verified") and email.get("email")
        ]
        primary_email = next((email for email in verified_emails if email.get("primary")), None)
        selected_email = primary_email or (verified_emails[0] if verified_emails else None)
        user_email = selected_email.get("email") if selected_email else None

        if not user_email:
            raise ValueError("Can't get user email from github")

        return User(
            login_type=cls._login_type,
            user_name=user_name,
            user_email=user_email,
            origin_data=origin_data
        )
