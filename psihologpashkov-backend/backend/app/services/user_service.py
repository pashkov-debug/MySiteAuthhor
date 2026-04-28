from typing import Protocol
from uuid import UUID

from app.schemas.user import UserUpdateRequest


class UserServiceError(Exception):
    pass


class UserNotFoundError(UserServiceError):
    pass


class UserForProfile(Protocol):
    id: UUID
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool


class UserProfileRepository(Protocol):
    async def get_by_id(self, user_id: UUID) -> UserForProfile | None:
        pass

    async def update_profile(
        self,
        user_id: UUID,
        full_name: str | None,
    ) -> UserForProfile | None:
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
