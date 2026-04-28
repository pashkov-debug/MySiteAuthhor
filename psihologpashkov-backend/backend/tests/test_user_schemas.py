import pytest
from app.schemas.user import UserPasswordChangeRequest, UserUpdateRequest
from pydantic import ValidationError


def test_user_update_request_normalizes_full_name() -> None:
    data = UserUpdateRequest(full_name="  Алексей Пашков  ")

    assert data.full_name == "Алексей Пашков"


def test_user_update_request_converts_blank_full_name_to_none() -> None:
    data = UserUpdateRequest(full_name="     ")

    assert data.full_name is None


def test_user_update_request_accepts_none_full_name() -> None:
    data = UserUpdateRequest(full_name=None)

    assert data.full_name is None


def test_user_password_change_request_accepts_valid_passwords() -> None:
    data = UserPasswordChangeRequest(
        current_password="old-password",
        new_password="new-password",
    )

    assert data.current_password == "old-password"
    assert data.new_password == "new-password"


def test_user_password_change_request_rejects_empty_current_password() -> None:
    with pytest.raises(ValidationError):
        UserPasswordChangeRequest(
            current_password="    ",
            new_password="new-password",
        )


def test_user_password_change_request_rejects_short_new_password() -> None:
    with pytest.raises(ValidationError):
        UserPasswordChangeRequest(
            current_password="old-password",
            new_password="short",
        )
