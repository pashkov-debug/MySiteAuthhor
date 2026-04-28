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

    cache_default_ttl_seconds: int = 300

    enable_openapi: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("API prefix must start with '/'")
        if value.endswith("/"):
            raise ValueError("API prefix must not end with '/'")
        return value

    @field_validator("jwt_access_ttl_minutes", "jwt_refresh_ttl_days", "cache_default_ttl_seconds")
    @classmethod
    def validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Value must be positive")
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
