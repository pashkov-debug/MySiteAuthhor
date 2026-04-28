import pytest
from app.schemas.auth import LoginRequest, RegisterRequest
from pydantic import ValidationError


def test_register_request_normalizes_email_and_full_name() -> None:
    data = RegisterRequest(
        email=" USER@Example.COM ",
        password="strong-password",
        full_name="  Алексей  ",
    )

    assert data.email == "user@example.com"
    assert data.full_name == "Алексей"


def test_register_request_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(email="invalid-email", password="strong-password")


def test_register_request_rejects_blank_password() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(email="user@example.com", password="        ")


def test_login_request_normalizes_email() -> None:
    data = LoginRequest(email=" USER@Example.COM ", password="password")

    assert data.email == "user@example.com"
