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
        "https://fd2a0955.temp-mail-30o.pages.dev"
    )

    # token settings
    cache_client_type: str = "upstash"
    redis_url: str = Field(default="", exclude=True)
    upstash_api_url: str = ""
    upstash_api_token: str = Field(default="", exclude=True)
    token_code_expire_seconds: int = 30

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
    email_rate_limit_timewindow_seconds: int = 60
    email_rate_limit_max_requests: int = 60
    cf_turnstile_site_key: str = ""
    cf_turnstile_secret_key: str = Field(default="", exclude=True)

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

settings = Settings()
_logger.info(f"settings: {settings.model_dump_json(indent=2)}")
