from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.api.deps import get_refresh_session_repository, get_user_repository
from app.core.config import Settings
from app.core.jwt import create_access_token
from app.core.security import hash_password, verify_password
from app.main import create_app
from fastapi.testclient import TestClient


@dataclass(slots=True)
class FakeUser:
    id: UUID
    email: str
    password_hash: str
    full_name: str | None
    is_active: bool = True
    is_superuser: bool = False
    email_verified_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class FakeUserRepository:
    users_by_id: dict[UUID, FakeUser] = field(default_factory=dict)

    async def get_by_id(self, user_id: UUID) -> FakeUser | None:
        return self.users_by_id.get(user_id)

    async def get_by_email(self, email: str) -> FakeUser | None:
        return None

    async def create_user(
        self,
        email: str,
        password_hash: str,
        full_name: str | None,
        is_active: bool = True,
    ) -> FakeUser:
        user = FakeUser(
            id=uuid4(),
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            is_active=is_active,
        )
        self.users_by_id[user.id] = user

        return user

    async def mark_email_verified(
        self,
        user_id: UUID,
        verified_at: datetime | None = None,
    ) -> FakeUser | None:
        user = self.users_by_id.get(user_id)

        if user is None:
            return None

        user.email_verified_at = verified_at or datetime.now(UTC)
        user.is_active = True
        user.updated_at = datetime.now(UTC)

        return user

    async def update_profile(
        self,
        user_id: UUID,
        full_name: str | None,
    ) -> FakeUser | None:
        user = self.users_by_id.get(user_id)

        if user is None:
            return None

        user.full_name = full_name
        user.updated_at = datetime.now(UTC)

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
        user.updated_at = datetime.now(UTC)

        return user


@dataclass(slots=True)
class FakeRefreshSessionRepository:
    revoked_user_ids: list[UUID] = field(default_factory=list)

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        self.revoked_user_ids.append(user_id)

        return 1


def make_password_client(
    test_settings: Settings,
) -> tuple[TestClient, FakeUserRepository, FakeRefreshSessionRepository, FakeUser]:
    app = create_app(test_settings)
    user_repository = FakeUserRepository()
    refresh_session_repository = FakeRefreshSessionRepository()
    user = FakeUser(
        id=uuid4(),
        email="user@example.com",
        password_hash=hash_password("old-password"),
        full_name=None,
    )
    user_repository.users_by_id[user.id] = user

    async def override_user_repository() -> FakeUserRepository:
        return user_repository

    async def override_refresh_session_repository() -> FakeRefreshSessionRepository:
        return refresh_session_repository

    app.dependency_overrides[get_user_repository] = override_user_repository
    app.dependency_overrides[get_refresh_session_repository] = override_refresh_session_repository

    return TestClient(app), user_repository, refresh_session_repository, user


def test_change_password_requires_authentication(test_settings: Settings) -> None:
    client, _, _, _ = make_password_client(test_settings)

    response = client.patch(
        "/api/v1/me/password",
        json={
            "current_password": "old-password",
            "new_password": "new-password",
        },
    )

    assert response.status_code == 401


def test_change_password_updates_hash_and_revokes_refresh_sessions(
    test_settings: Settings,
) -> None:
    client, _, refresh_session_repository, user = make_password_client(test_settings)
    access_token = create_access_token(str(user.id), test_settings)

    response = client.patch(
        "/api/v1/me/password",
        json={
            "current_password": "old-password",
            "new_password": "new-password",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"
    assert verify_password("new-password", user.password_hash)
    assert refresh_session_repository.revoked_user_ids == [user.id]


def test_change_password_rejects_invalid_current_password(
    test_settings: Settings,
) -> None:
    client, _, _, user = make_password_client(test_settings)
    access_token = create_access_token(str(user.id), test_settings)

    response = client.patch(
        "/api/v1/me/password",
        json={
            "current_password": "wrong-password",
            "new_password": "new-password",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid current password"


def test_change_password_rejects_same_password(test_settings: Settings) -> None:
    client, _, _, user = make_password_client(test_settings)
    access_token = create_access_token(str(user.id), test_settings)

    response = client.patch(
        "/api/v1/me/password",
        json={
            "current_password": "old-password",
            "new_password": "old-password",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "New password must differ from current password"
