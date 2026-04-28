from typing import Protocol
from uuid import UUID

from app.core.security import hash_password, verify_password
from app.schemas.user import UserPasswordChangeRequest, UserUpdateRequest


class UserServiceError(Exception):
    pass


class UserNotFoundError(UserServiceError):
    pass


class InvalidCurrentPasswordError(UserServiceError):
    pass


class NewPasswordMustDifferError(UserServiceError):
    pass


class UserForProfile(Protocol):
    id: UUID
    email: str
    full_name: str | None
    avatar_path: str | None
    is_active: bool
    is_superuser: bool


class UserForPasswordChange(UserForProfile, Protocol):
    password_hash: str


class UserProfileRepository(Protocol):
    async def get_by_id(self, user_id: UUID) -> UserForProfile | None:
        pass

    async def update_profile(
        self,
        user_id: UUID,
        full_name: str | None,
    ) -> UserForProfile | None:
        pass

    async def update_password_hash(
        self,
        user_id: UUID,
        password_hash: str,
    ) -> UserForPasswordChange | None:
        pass

    async def update_avatar_path(
        self,
        user_id: UUID,
        avatar_path: str | None,
    ) -> UserForProfile | None:
        pass


class RefreshSessionRevocationRepository(Protocol):
    async def revoke_all_for_user(self, user_id: UUID) -> int:
        pass


async def update_current_user_profile(
    user_id: UUID,
    data: UserUpdateRequest,
    user_repository: UserProfileRepository,
) -> UserForProfile:
    user = await user_repository.update_profile(
        user_id=user_id,
        full_name=data.full_name,
    )

    if user is None:
        raise UserNotFoundError("User not found")

    return user


async def update_current_user_avatar(
    user_id: UUID,
    avatar_path: str | None,
    user_repository: UserProfileRepository,
) -> UserForProfile:
    user = await user_repository.update_avatar_path(
        user_id=user_id,
        avatar_path=avatar_path,
    )

    if user is None:
        raise UserNotFoundError("User not found")

    return user


async def change_current_user_password(
    current_user: UserForPasswordChange,
    data: UserPasswordChangeRequest,
    user_repository: UserProfileRepository,
    refresh_session_repository: RefreshSessionRevocationRepository,
) -> UserForPasswordChange:
    if not verify_password(data.current_password, current_user.password_hash):
        raise InvalidCurrentPasswordError("Invalid current password")

    if verify_password(data.new_password, current_user.password_hash):
        raise NewPasswordMustDifferError("New password must differ from current password")

    updated_user = await user_repository.update_password_hash(
        user_id=current_user.id,
        password_hash=hash_password(data.new_password),
    )

    if updated_user is None:
        raise UserNotFoundError("User not found")

    await refresh_session_repository.revoke_all_for_user(current_user.id)

    return updated_user
