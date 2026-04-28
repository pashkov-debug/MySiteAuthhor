from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.api.deps import get_refresh_session_repository, get_user_repository
from app.core.config import Settings
from app.core.jwt import create_access_token
from app.core.security import hash_password
from app.main import create_app
from fastapi.testclient import TestClient


@dataclass(slots=True)
class FakeUser:
    id: UUID
    email: str
    password_hash: str
    full_name: str | None
    avatar_path: str | None = None
    is_active: bool = True
    is_superuser: bool = False
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
    ) -> FakeUser:
        user = FakeUser(
            id=uuid4(),
            email=email,
            password_hash=password_hash,
            full_name=full_name,
        )
        self.users_by_id[user.id] = user

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

    async def update_avatar_path(
        self,
        user_id: UUID,
        avatar_path: str | None,
    ) -> FakeUser | None:
        user = self.users_by_id.get(user_id)

        if user is None:
            return None

        user.avatar_path = avatar_path
        user.updated_at = datetime.now(UTC)

        return user


@dataclass(slots=True)
class FakeRefreshSessionRepository:
    async def revoke_all_for_user(self, user_id: UUID) -> int:
        return 0


def make_avatar_client(
    test_settings: Settings,
    tmp_path: Path,
) -> tuple[TestClient, FakeUserRepository, FakeUser]:
    uploads_root = tmp_path / "uploads"

    app = create_app(
        test_settings.model_copy(
            update={
                "uploads_root": str(uploads_root),
                "uploads_public_path": "/uploads",
                "avatar_max_size_bytes": 1024,
            }
        )
    )
    user_repository = FakeUserRepository()
    refresh_session_repository = FakeRefreshSessionRepository()

    user = FakeUser(
        id=uuid4(),
        email="user@example.com",
        password_hash=hash_password("password"),
        full_name=None,
    )
    user_repository.users_by_id[user.id] = user

    async def override_user_repository() -> FakeUserRepository:
        return user_repository

    async def override_refresh_session_repository() -> FakeRefreshSessionRepository:
        return refresh_session_repository

    app.dependency_overrides[get_user_repository] = override_user_repository
    app.dependency_overrides[get_refresh_session_repository] = override_refresh_session_repository

    return TestClient(app), user_repository, user


def test_upload_avatar_requires_authentication(
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    client, _, _ = make_avatar_client(test_settings, tmp_path)

    response = client.patch(
        "/api/v1/me/avatar",
        files={"file": ("avatar.png", b"avatar-content", "image/png")},
    )

    assert response.status_code == 401


def test_upload_avatar_saves_file_and_updates_user(
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    client, _, user = make_avatar_client(test_settings, tmp_path)
    access_token = create_access_token(str(user.id), test_settings)

    response = client.patch(
        "/api/v1/me/avatar",
        files={"file": ("avatar.png", b"avatar-content", "image/png")},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["avatar_path"].startswith(f"/uploads/avatars/{user.id}/")
    assert body["avatar_path"].endswith(".png")

    file_path = tmp_path / body["avatar_path"].lstrip("/")
    assert file_path.is_file()
    assert file_path.read_bytes() == b"avatar-content"


def test_upload_avatar_rejects_unsupported_extension(
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    client, _, user = make_avatar_client(test_settings, tmp_path)
    access_token = create_access_token(str(user.id), test_settings)

    response = client.patch(
        "/api/v1/me/avatar",
        files={"file": ("avatar.gif", b"avatar-content", "image/gif")},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported avatar file extension"


def test_upload_avatar_rejects_too_large_file(
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    client, _, user = make_avatar_client(test_settings, tmp_path)
    access_token = create_access_token(str(user.id), test_settings)

    response = client.patch(
        "/api/v1/me/avatar",
        files={"file": ("avatar.png", b"x" * 2048, "image/png")},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 413


def test_delete_avatar_clears_user_avatar_and_removes_file(
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    client, _, user = make_avatar_client(test_settings, tmp_path)
    access_token = create_access_token(str(user.id), test_settings)

    upload_response = client.patch(
        "/api/v1/me/avatar",
        files={"file": ("avatar.png", b"avatar-content", "image/png")},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    avatar_path = upload_response.json()["avatar_path"]
    file_path = tmp_path / avatar_path.lstrip("/")

    assert file_path.is_file()

    delete_response = client.delete(
        "/api/v1/me/avatar",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["avatar_path"] is None
    assert user.avatar_path is None
    assert not file_path.exists()
