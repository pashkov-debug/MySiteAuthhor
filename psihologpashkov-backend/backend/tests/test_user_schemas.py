from app.schemas.user import UserUpdateRequest


def test_user_update_request_normalizes_full_name() -> None:
    data = UserUpdateRequest(full_name="  Алексей Пашков  ")

    assert data.full_name == "Алексей Пашков"


def test_user_update_request_converts_blank_full_name_to_none() -> None:
    data = UserUpdateRequest(full_name="     ")

    assert data.full_name is None


def test_user_update_request_accepts_none_full_name() -> None:
    data = UserUpdateRequest(full_name=None)

    assert data.full_name is None
