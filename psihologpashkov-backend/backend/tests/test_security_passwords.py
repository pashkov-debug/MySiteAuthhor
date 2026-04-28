import pytest
from app.core.security import hash_password, verify_password


def test_hash_password_returns_non_plain_hash() -> None:
    password = "strong-password-123"

    hashed_password = hash_password(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password)


def test_verify_password_rejects_wrong_password() -> None:
    hashed_password = hash_password("correct-password")

    assert not verify_password("wrong-password", hashed_password)


def test_verify_password_rejects_invalid_hash() -> None:
    assert not verify_password("password", "not-a-valid-hash")


def test_hash_password_rejects_empty_password() -> None:
    with pytest.raises(ValueError, match="Password must not be empty"):
        hash_password("")
