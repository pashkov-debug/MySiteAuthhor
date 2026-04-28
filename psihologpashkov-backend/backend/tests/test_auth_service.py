from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from app.core.config import Settings
from app.core.jwt import decode_token
from app.core.security import verify_password
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_service import (
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    authenticate_user,
    create_token_pair,
    register_user,
)


@dataclass(slots=True)
class FakeUser:
    id: UUID
    email: str
    password_hash: str
    is_active: bool = True
    full_name: str | None = None


@dataclass(slots=True)
class FakeUserRepository:
    users_by_email: dict[str, FakeUser] = field(default_factory=dict)

    async def get_by_email(self, email: str) -> FakeUser | None:
        return self.users_by_email.get(email)

    async def create_user(
        self,
        email: str,
        password_hash: str,
        full_name: str | None,
    ) -> FakeUser:
        user = FakeUser(
            id=uuid4(),
            email=email,
            password_hash=password_hash,
            full_name=full_name,
        )
        self.users_by_email[email] = user

        return user


async def test_register_user_creates_user_with_hashed_password() -> None:
    repository = FakeUserRepository()
    request = RegisterRequest(
        email="USER@example.com",
        password="strong-password",
        full_name="User",
    )

    user = await register_user(request, repository)

    assert user.email == "user@example.com"
    assert user.password_hash != "strong-password"
    assert verify_password("strong-password", user.password_hash)


async def test_register_user_rejects_existing_email() -> None:
    repository = FakeUserRepository()
    request = RegisterRequest(email="user@example.com", password="strong-password")

    await register_user(request, repository)

    with pytest.raises(UserAlreadyExistsError):
        await register_user(request, repository)


async def test_authenticate_user_accepts_valid_credentials() -> None:
    repository = FakeUserRepository()
    register_request = RegisterRequest(email="user@example.com", password="strong-password")
    login_request = LoginRequest(email="user@example.com", password="strong-password")

    created_user = await register_user(register_request, repository)
    authenticated_user = await authenticate_user(login_request, repository)

    assert authenticated_user.id == created_user.id


async def test_authenticate_user_rejects_wrong_password() -> None:
    repository = FakeUserRepository()
    register_request = RegisterRequest(email="user@example.com", password="strong-password")
    login_request = LoginRequest(email="user@example.com", password="wrong-password")

    await register_user(register_request, repository)

    with pytest.raises(InvalidCredentialsError):
        await authenticate_user(login_request, repository)


async def test_authenticate_user_rejects_inactive_user() -> None:
    repository = FakeUserRepository()
    register_request = RegisterRequest(email="user@example.com", password="strong-password")
    login_request = LoginRequest(email="user@example.com", password="strong-password")

    user = await register_user(register_request, repository)
    user.is_active = False

    with pytest.raises(InactiveUserError):
        await authenticate_user(login_request, repository)


def test_create_token_pair_returns_decodable_tokens(test_settings: Settings) -> None:
    user_id = uuid4()

    token_pair = create_token_pair(user_id, test_settings)

    access_payload = decode_token(
        token_pair.access_token,
        expected_type="access",
        settings=test_settings,
    )
    refresh_payload = decode_token(
        token_pair.refresh_token,
        expected_type="refresh",
        settings=test_settings,
    )

    assert access_payload.sub == str(user_id)
    assert refresh_payload.sub == str(user_id)
    assert token_pair.token_type == "bearer"
    assert token_pair.expires_in == 900
