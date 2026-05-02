from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TokenPayload(BaseModel):
    sub: str
    type: Literal["access", "refresh"]
    exp: int
    iat: int
    jti: str


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_value(value)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()

        return normalized or None


class RegisterResponse(BaseModel):
    status: Literal["email_verification_required"] = "email_verification_required"
    email: str
    full_name: str | None = None


class EmailVerificationResendRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class EmailVerificationResponse(BaseModel):
    status: Literal["ok"] = "ok"


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value:
            raise ValueError("Password must not be empty")

        return value


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=1)

    @field_validator("refresh_token")
    @classmethod
    def validate_refresh_token(cls, value: str | None) -> str | None:
        if value is None:
            return None

        if not value.strip():
            raise ValueError("Refresh token must not be empty")

        return value


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class LogoutResponse(BaseModel):
    status: Literal["ok"] = "ok"


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()

    if "@" not in normalized:
        raise ValueError("Email must contain '@'")

    local_part, _, domain = normalized.partition("@")

    if not local_part or not domain or "." not in domain:
        raise ValueError("Email is invalid")

    return normalized


def validate_password_value(value: str) -> str:
    if not value or not value.strip():
        raise ValueError("Password must not be empty")

    return value
