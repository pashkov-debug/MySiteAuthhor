from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

import jwt as pyjwt
from jwt import ExpiredSignatureError, PyJWTError
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.schemas.auth import TokenPayload

TokenType = Literal["access", "refresh"]

RESERVED_CLAIMS = {"sub", "type", "exp", "iat", "jti"}


class TokenError(Exception):
    pass


class ExpiredTokenError(TokenError):
    pass


class InvalidTokenError(TokenError):
    pass


class TokenTypeMismatchError(InvalidTokenError):
    pass


def create_access_token(
    subject: str,
    settings: Settings | None = None,
    extra_claims: dict[str, object] | None = None,
) -> str:
    app_settings = settings or get_settings()

    return create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=app_settings.jwt_access_ttl_minutes),
        settings=app_settings,
        extra_claims=extra_claims,
    )


def create_refresh_token(
    subject: str,
    settings: Settings | None = None,
    extra_claims: dict[str, object] | None = None,
) -> str:
    app_settings = settings or get_settings()

    return create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(days=app_settings.jwt_refresh_ttl_days),
        settings=app_settings,
        extra_claims=extra_claims,
    )


def create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    settings: Settings | None = None,
    extra_claims: dict[str, object] | None = None,
) -> str:
    if not subject:
        raise ValueError("Token subject must not be empty")

    if extra_claims and RESERVED_CLAIMS.intersection(extra_claims):
        raise ValueError("Extra claims must not override reserved JWT claims")

    app_settings = settings or get_settings()
    issued_at = datetime.now(UTC)
    expires_at = issued_at + expires_delta

    payload: dict[str, object] = {
        "sub": subject,
        "type": token_type,
        "iat": issued_at,
        "exp": expires_at,
        "jti": str(uuid4()),
    }

    if extra_claims:
        payload.update(extra_claims)

    secret = get_token_secret(token_type, app_settings)

    return pyjwt.encode(
        payload,
        secret,
        algorithm=app_settings.jwt_algorithm,
    )


def decode_token(
    token: str,
    expected_type: TokenType,
    settings: Settings | None = None,
) -> TokenPayload:
    if not token:
        raise InvalidTokenError("Token must not be empty")

    app_settings = settings or get_settings()
    secret = get_token_secret(expected_type, app_settings)

    try:
        raw_payload = pyjwt.decode(
            token,
            secret,
            algorithms=[app_settings.jwt_algorithm],
        )
    except ExpiredSignatureError as exc:
        raise ExpiredTokenError("Token has expired") from exc
    except PyJWTError as exc:
        raise InvalidTokenError("Token is invalid") from exc

    try:
        payload = TokenPayload.model_validate(raw_payload)
    except ValidationError as exc:
        raise InvalidTokenError("Token payload is invalid") from exc

    if payload.type != expected_type:
        raise TokenTypeMismatchError("Token type mismatch")

    return payload


def get_token_secret(token_type: TokenType, settings: Settings) -> str:
    if token_type == "access":
        return settings.jwt_access_secret

    return settings.jwt_refresh_secret
