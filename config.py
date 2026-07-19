import logging
from typing import Dict

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(
    format="%(asctime)s: %(levelname)s: %(name)s: %(message)s",
    level=logging.INFO
)
_logger = logging.getLogger(__name__)


class AppSettings(BaseModel):
    app_id: str
    app_secret: str
    redirect_url: str
    token_expire_days: int = 30


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    debug: bool = False
    cors_allow_origins: str = (
        "http://localhost:5173,"
        "http://localhost,"
        "http://127.0.0.1,"
        "https://mail.cerise-bouquet.xyz,"
        "https://fd2a0955.temp-mail-30o.pages.dev,"
        "https://live.neofantasy.online,"
        "https://api.neofantasy.online,"
        "https://auth.neofantasy.online,"
        "https://auth-live-ten.vercel.app"
    )

    # token settings
    cache_client_type: str = "upstash"
    redis_url: str = Field(default="", exclude=True)
    upstash_api_url: str = ""
    upstash_api_token: str = Field(default="", exclude=True)
    token_code_expire_seconds: int = 30
    auth_jwt_secret: str = Field(default="", exclude=True)
    # Keep sessions short enough that a leaked browser token has a bounded
    # lifetime. Deployments can choose a shorter value through the environment.
    auth_token_expire_days: int = 7
    auth_cookie_name: str = "nf_session"
    auth_cookie_domain: str = ""
    auth_issuer: str = "neofantasy-auth"
    auth_audience: str = "neofantasy"
    admin_emails: str = ""

    # db settings
    enabled_db: bool = False
    db_client_type: str = "supabase_rest"
    supabase_api_url: str = ""
    supabase_api_key: str = Field(default="", exclude=True)
    sqlite_db_url: str = "sqlite:///db.sqlite3"

    # smtp settings
    enabled_smtp: bool = False
    mail_client_type: str = "smtp"
    smtp_url: str = Field(default="", exclude=True)
    verify_code_expire_seconds: int = 120
    email_rate_limit_timewindow_seconds: int = 300
    email_rate_limit_max_requests: int = 3
    login_rate_limit_timewindow_seconds: int = 300
    login_rate_limit_max_requests: int = 10
    verification_attempt_timewindow_seconds: int = 300
    verification_attempt_max_requests: int = 5
    cf_turnstile_site_key: str = ""
    cf_turnstile_secret_key: str = Field(default="", exclude=True)
    cf_turnstile_allowed_hostnames: str = "neofantasy.online,auth-live-ten.vercel.app"

    # oauth settings
    google_client_id: str = ""
    google_client_secret: str = Field(default="", exclude=True)
    github_client_id: str = ""
    github_client_secret: str = Field(default="", exclude=True)
    ms_client_id: str = ""
    ms_client_secret: str = Field(default="", exclude=True)
    enabled_web3_client: bool = True

    # app settings
    app_settings: Dict[str, AppSettings] = Field(default={}, exclude=True)

    # temp-mail worker bridge, backend only
    temp_mail_api_base: str = ""
    temp_mail_admin_auth: str = Field(default="", exclude=True)
    temp_mail_user_max_address_count: int = 50
    temp_mail_account_send_balance: int = 10

    @field_validator('app_settings')
    def convert_app_settings(cls, values: Dict[str, AppSettings]):
        return {
            app_settings.app_id: app_settings
            for _, app_settings in values.items()
        }

    @field_validator('debug', mode='before')
    def parse_debug(cls, value):
        if isinstance(value, str) and value.lower() in {
            "release", "prod", "production", "vercel", "none", ""
        }:
            return False
        return value

    def get_cors_allow_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allow_origins.split(",")
            if origin.strip()
        ]

    def get_admin_emails(self) -> set[str]:
        return {
            email.strip().lower()
            for email in self.admin_emails.split(",")
            if email.strip()
        }

    def get_turnstile_allowed_hostnames(self) -> set[str]:
        return {
            hostname.strip().lower().rstrip(".")
            for hostname in self.cf_turnstile_allowed_hostnames.split(",")
            if hostname.strip()
        }

settings = Settings()
_logger.info(f"settings: {settings.model_dump_json(indent=2)}")
