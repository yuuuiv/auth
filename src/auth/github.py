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


class GithubAuthClient(AuthClientBase):

    _login_type = "github"

    @classmethod
    def get_login_url(cls, redirect_url: str = "") -> str:
        params = {
            "client_id": settings.github_client_id,
            "scope": "user:email",
        }
        if redirect_url:
            params["redirect_uri"] = redirect_url
        return f"{GITHUB_URL}?{urlencode(params)}"

    @classmethod
    def get_user(cls, oauth_body: OauthBody) -> Optional[User]:
        if not oauth_body.code:
            return None
        token_res = requests.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": oauth_body.code,
                "redirect_uri": oauth_body.redirect_url or None,
            },
            headers={"Accept": "application/json"}
        ).json()
        if not token_res.get('access_token'):
            raise ValueError("Can't get access token from github")
        access_token = token_res['access_token']
        res = requests.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"token {access_token}",
                "Accept": "application/json"
            }
        ).json()
        user_name = res.get('login')
        user_email = res.get('email')
        origin_data = res

        if not user_name:
            raise ValueError("Can't get user name from github")

        if not user_email:
            res = requests.get(
                GITHUB_EMAIL_URL,
                headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/json"
                }
            ).json()
            fallback_emails = []
            for email in res:
                fallback_emails.append(email.get('email'))
                if email.get('primary'):
                    user_email = email.get('email')
                    break
            user_email = user_email or fallback_emails[0]

        if not user_email:
            raise ValueError("Can't get user email from github")

        return User(
            login_type=cls._login_type,
            user_name=user_name,
            user_email=user_email,
            origin_data=origin_data
        )
