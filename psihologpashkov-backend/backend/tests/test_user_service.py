from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from app.core.security import hash_password, verify_password
from app.schemas.user import UserPasswordChangeRequest, UserUpdateRequest
from app.services.user_service import (
    InvalidCurrentPasswordError,
    NewPasswordMustDifferError,
    UserNotFoundError,
    change_current_user_password,
    update_current_user_profile,
)


@dataclass(slots=True)
class FakeUser:
    id: UUID
    email: str
    full_name: str | None
    password_hash: str = field(default_factory=lambda: hash_password("old-password"))
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

    async def update_password_hash(
        self,
        user_id: UUID,
        password_hash: str,
    ) -> FakeUser | None:
        user = self.users_by_id.get(user_id)

        if user is None:
            return None

        user.password_hash = password_hash

        return user


@dataclass(slots=True)
class FakeRefreshSessionRepository:
    revoked_user_ids: list[UUID] = field(default_factory=list)

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        self.revoked_user_ids.append(user_id)

        return 1


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


async def test_change_current_user_password_updates_hash_and_revokes_sessions() -> None:
    user = FakeUser(
        id=uuid4(),
        email="user@example.com",
        full_name=None,
    )
    user_repository = FakeUserRepository(users_by_id={user.id: user})
    refresh_session_repository = FakeRefreshSessionRepository()
    request = UserPasswordChangeRequest(
        current_password="old-password",
        new_password="new-password",
    )

    updated_user = await change_current_user_password(
        current_user=user,
        data=request,
        user_repository=user_repository,
        refresh_session_repository=refresh_session_repository,
    )

    assert verify_password("new-password", updated_user.password_hash)
    assert not verify_password("old-password", updated_user.password_hash)
    assert refresh_session_repository.revoked_user_ids == [user.id]


async def test_change_current_user_password_rejects_invalid_current_password() -> None:
    user = FakeUser(
        id=uuid4(),
        email="user@example.com",
        full_name=None,
    )
    user_repository = FakeUserRepository(users_by_id={user.id: user})
    refresh_session_repository = FakeRefreshSessionRepository()
    request = UserPasswordChangeRequest(
        current_password="wrong-password",
        new_password="new-password",
    )

    with pytest.raises(InvalidCurrentPasswordError):
        await change_current_user_password(
            current_user=user,
            data=request,
            user_repository=user_repository,
            refresh_session_repository=refresh_session_repository,
        )


async def test_change_current_user_password_rejects_same_password() -> None:
    user = FakeUser(
        id=uuid4(),
        email="user@example.com",
        full_name=None,
    )
    user_repository = FakeUserRepository(users_by_id={user.id: user})
    refresh_session_repository = FakeRefreshSessionRepository()
    request = UserPasswordChangeRequest(
        current_password="old-password",
        new_password="old-password",
    )

    with pytest.raises(NewPasswordMustDifferError):
        await change_current_user_password(
            current_user=user,
            data=request,
            user_repository=user_repository,
            refresh_session_repository=refresh_session_repository,
        )


async def test_change_current_user_password_rejects_missing_user() -> None:
    user = FakeUser(
        id=uuid4(),
        email="user@example.com",
        full_name=None,
    )
    user_repository = FakeUserRepository()
    refresh_session_repository = FakeRefreshSessionRepository()
    request = UserPasswordChangeRequest(
        current_password="old-password",
        new_password="new-password",
    )

    with pytest.raises(UserNotFoundError):
        await change_current_user_password(
            current_user=user,
            data=request,
            user_repository=user_repository,
            refresh_session_repository=refresh_session_repository,
        )
