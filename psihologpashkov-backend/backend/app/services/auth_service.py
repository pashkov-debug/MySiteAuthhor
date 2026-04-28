from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.core.config import Settings, get_settings
from app.core.jwt import create_access_token, create_refresh_token
from app.core.security import hash_password, verify_password
from app.schemas.auth import LoginRequest, RegisterRequest


class AuthServiceError(Exception):
    pass


class UserAlreadyExistsError(AuthServiceError):
    pass


class InvalidCredentialsError(AuthServiceError):
    pass


class InactiveUserError(AuthServiceError):
    pass


class UserForAuth(Protocol):
    id: UUID
    email: str
    password_hash: str
    is_active: bool


class UserRepository(Protocol):
    async def get_by_email(self, email: str) -> UserForAuth | None:
        pass

    async def create_user(
        self,
        email: str,
        password_hash: str,
        full_name: str | None,
    ) -> UserForAuth:
        pass


@dataclass(frozen=True, slots=True)
class AuthTokenPair:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


async def register_user(
    data: RegisterRequest,
    user_repository: UserRepository,
) -> UserForAuth:
    existing_user = await user_repository.get_by_email(data.email)

    if existing_user is not None:
        raise UserAlreadyExistsError("User already exists")

    return await user_repository.create_user(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
    )


async def authenticate_user(
    data: LoginRequest,
    user_repository: UserRepository,
) -> UserForAuth:
    user = await user_repository.get_by_email(data.email)

    if user is None:
        raise InvalidCredentialsError("Invalid email or password")

    if not verify_password(data.password, user.password_hash):
        raise InvalidCredentialsError("Invalid email or password")

    if not user.is_active:
        raise InactiveUserError("User is inactive")

    return user


def create_token_pair(
    subject: UUID | str,
    settings: Settings | None = None,
) -> AuthTokenPair:
    app_settings = settings or get_settings()
    subject_value = str(subject)

    return AuthTokenPair(
        access_token=create_access_token(subject_value, app_settings),
        refresh_token=create_refresh_token(subject_value, app_settings),
        token_type="bearer",
        expires_in=app_settings.jwt_access_ttl_minutes * 60,
    )
