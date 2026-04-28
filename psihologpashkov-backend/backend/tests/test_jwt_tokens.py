from datetime import timedelta

import pytest
from app.core.config import Settings
from app.core.jwt import (
    InvalidTokenError,
    TokenTypeMismatchError,
    create_access_token,
    create_refresh_token,
    create_token,
    decode_token,
)


def test_access_token_round_trip(test_settings: Settings) -> None:
    token = create_access_token("user-1", test_settings)

    payload = decode_token(token, expected_type="access", settings=test_settings)

    assert payload.sub == "user-1"
    assert payload.type == "access"
    assert payload.jti


def test_refresh_token_round_trip(test_settings: Settings) -> None:
    token = create_refresh_token("user-1", test_settings)

    payload = decode_token(token, expected_type="refresh", settings=test_settings)

    assert payload.sub == "user-1"
    assert payload.type == "refresh"
    assert payload.jti


def test_decode_token_rejects_refresh_token_as_access_token(test_settings: Settings) -> None:
    token = create_refresh_token("user-1", test_settings)

    with pytest.raises(InvalidTokenError):
        decode_token(token, expected_type="access", settings=test_settings)


def test_decode_token_rejects_wrong_token_type_when_secrets_match(
    test_settings: Settings,
) -> None:
    same_secret_settings = test_settings.model_copy(
        update={
            "jwt_access_secret": "same-test-secret-32-bytes-minimum-value",
            "jwt_refresh_secret": "same-test-secret-32-bytes-minimum-value",
        }
    )
    token = create_refresh_token("user-1", same_secret_settings)

    with pytest.raises(TokenTypeMismatchError):
        decode_token(token, expected_type="access", settings=same_secret_settings)


def test_decode_token_rejects_invalid_token(test_settings: Settings) -> None:
    with pytest.raises(InvalidTokenError):
        decode_token("invalid-token", expected_type="access", settings=test_settings)


def test_create_token_rejects_empty_subject(test_settings: Settings) -> None:
    with pytest.raises(ValueError, match="Token subject must not be empty"):
        create_access_token("", test_settings)


def test_create_token_rejects_reserved_extra_claims(test_settings: Settings) -> None:
    with pytest.raises(ValueError, match="reserved JWT claims"):
        create_token(
            subject="user-1",
            token_type="access",
            expires_delta=timedelta(minutes=15),
            settings=test_settings,
            extra_claims={"sub": "user-2"},
        )
