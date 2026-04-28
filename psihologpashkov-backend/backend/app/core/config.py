from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Psiholog Pashkov API"
    app_env: Literal["local", "test", "stage", "prod"] = "local"
    api_v1_prefix: str = "/api/v1"

    cors_origins: str = Field(default="https://psihologpashkov.ru,https://www.psihologpashkov.ru")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/psihologpashkov"

    jwt_access_secret: str = "change-me-access-secret"
    jwt_refresh_secret: str = "change-me-refresh-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 30

    auth_refresh_cookie_name: str = "refresh_token"
    auth_refresh_cookie_domain: str | None = None
    auth_refresh_cookie_path: str = "/api/v1/auth"
    auth_refresh_cookie_secure: bool = True
    auth_refresh_cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    cache_default_ttl_seconds: int = 300

    enable_openapi: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("api_v1_prefix", "auth_refresh_cookie_path")
    @classmethod
    def validate_url_prefix(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("URL prefix must start with '/'")
        if value != "/" and value.endswith("/"):
            raise ValueError("URL prefix must not end with '/'")
        return value

    @field_validator(
        "jwt_access_ttl_minutes",
        "jwt_refresh_ttl_days",
        "cache_default_ttl_seconds",
    )
    @classmethod
    def validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Value must be positive")
        return value

    @field_validator("auth_refresh_cookie_domain", mode="before")
    @classmethod
    def normalize_cookie_domain(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()

        return normalized or None

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
