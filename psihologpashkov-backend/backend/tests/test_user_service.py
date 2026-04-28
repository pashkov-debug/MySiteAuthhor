from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from app.schemas.user import UserUpdateRequest
from app.services.user_service import UserNotFoundError, update_current_user_profile


@dataclass(slots=True)
class FakeUser:
    id: UUID
    email: str
    full_name: str | None
    is_active: bool = True
    is_superuser: bool = False


@dataclass(slots=True)
class FakeUserRepository:
    users_by_id: dict[UUID, FakeUser] = field(default_factory=dict)

    async def get_by_id(self, user_id: UUID) -> FakeUser | None:
        return self.users_by_id.get(user_id)

    async def update_profile(
        self,
        user_id: UUID,
        full_name: str | None,
    ) -> FakeUser | None:
        user = self.users_by_id.get(user_id)

        if user is None:
            return None

        user.full_name = full_name

        return user


async def test_update_current_user_profile_updates_full_name() -> None:
    user = FakeUser(
        id=uuid4(),
        email="user@example.com",
        full_name=None,
    )
    repository = FakeUserRepository(users_by_id={user.id: user})
    request = UserUpdateRequest(full_name="  Алексей  ")

    updated_user = await update_current_user_profile(
        user_id=user.id,
        data=request,
        user_repository=repository,
    )

    assert updated_user.full_name == "Алексей"


async def test_update_current_user_profile_can_clear_full_name() -> None:
    user = FakeUser(
        id=uuid4(),
        email="user@example.com",
        full_name="Алексей",
    )
    repository = FakeUserRepository(users_by_id={user.id: user})
    request = UserUpdateRequest(full_name="   ")

    updated_user = await update_current_user_profile(
        user_id=user.id,
        data=request,
        user_repository=repository,
    )

    assert updated_user.full_name is None


async def test_update_current_user_profile_rejects_missing_user() -> None:
    repository = FakeUserRepository()
    request = UserUpdateRequest(full_name="Алексей")

    with pytest.raises(UserNotFoundError):
        await update_current_user_profile(
            user_id=uuid4(),
            data=request,
            user_repository=repository,
        )
