from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserPublic(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    avatar_path: str | None = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()

        return normalized or None


class UserPasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("current_password")
    @classmethod
    def validate_current_password(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Current password must not be empty")

        return value

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("New password must not be empty")

        return value
