from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.api.deps import get_refresh_session_repository, get_user_repository
from app.core.config import Settings
from app.core.security import hash_password
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
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class FakeRefreshSession:
    id: UUID
    user_id: UUID
    jti_hash: str
    expires_at: datetime
    revoked_at: datetime | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class FakeUserRepository:
    users_by_id: dict[UUID, FakeUser] = field(default_factory=dict)
    users_by_email: dict[str, FakeUser] = field(default_factory=dict)

    async def get_by_id(self, user_id: UUID) -> FakeUser | None:
        return self.users_by_id.get(user_id)

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
        self.users_by_id[user.id] = user
        self.users_by_email[email] = user

        return user


@dataclass(slots=True)
class FakeRefreshSessionRepository:
    sessions_by_jti_hash: dict[str, FakeRefreshSession] = field(default_factory=dict)

    async def create_session(
        self,
        user_id: UUID,
        jti_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> FakeRefreshSession:
        refresh_session = FakeRefreshSession(
            id=uuid4(),
            user_id=user_id,
            jti_hash=jti_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.sessions_by_jti_hash[jti_hash] = refresh_session

        return refresh_session

    async def get_by_jti_hash(self, jti_hash: str) -> FakeRefreshSession | None:
        return self.sessions_by_jti_hash.get(jti_hash)

    async def revoke_by_jti_hash(self, jti_hash: str) -> bool:
        refresh_session = self.sessions_by_jti_hash.get(jti_hash)

        if refresh_session is None:
            return False

        if refresh_session.revoked_at is None:
            refresh_session.revoked_at = datetime.now(UTC)

        return True


def make_auth_client(
    test_settings: Settings,
) -> tuple[TestClient, FakeUserRepository, FakeRefreshSessionRepository]:
    app = create_app(test_settings)
    user_repository = FakeUserRepository()
    refresh_session_repository = FakeRefreshSessionRepository()

    async def override_user_repository() -> FakeUserRepository:
        return user_repository

    async def override_refresh_session_repository() -> FakeRefreshSessionRepository:
        return refresh_session_repository

    app.dependency_overrides[get_user_repository] = override_user_repository
    app.dependency_overrides[get_refresh_session_repository] = override_refresh_session_repository

    return TestClient(app), user_repository, refresh_session_repository


def test_register_creates_user(test_settings: Settings) -> None:
    client, _, _ = make_auth_client(test_settings)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": " USER@example.COM ",
            "password": "strong-password",
            "full_name": "  User Name  ",
        },
    )

    assert response.status_code == 201
    body = response.json()

    assert body["email"] == "user@example.com"
    assert body["full_name"] == "User Name"
    assert "password_hash" not in body


def test_register_rejects_existing_user(test_settings: Settings) -> None:
    client, _, _ = make_auth_client(test_settings)
    payload = {
        "email": "user@example.com",
        "password": "strong-password",
    }

    first_response = client.post("/api/v1/auth/register", json=payload)
    second_response = client.post("/api/v1/auth/register", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_login_returns_token_pair(test_settings: Settings) -> None:
    client, _, refresh_session_repository = make_auth_client(test_settings)

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert len(refresh_session_repository.sessions_by_jti_hash) == 1


def test_login_rejects_wrong_password(test_settings: Settings) -> None:
    client, _, _ = make_auth_client(test_settings)

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "user@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401


def test_me_requires_authentication(test_settings: Settings) -> None:
    client, _, _ = make_auth_client(test_settings)

    response = client.get("/api/v1/me")

    assert response.status_code == 401


def test_me_returns_current_user(test_settings: Settings) -> None:
    client, _, _ = make_auth_client(test_settings)

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


def test_me_rejects_inactive_user(test_settings: Settings) -> None:
    client, user_repository, _ = make_auth_client(test_settings)

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )
    user = user_repository.users_by_email["user@example.com"]
    user.is_active = False

    token_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )

    assert token_response.status_code == 403


def test_me_rejects_token_for_unknown_user(test_settings: Settings) -> None:
    client, user_repository, _ = make_auth_client(test_settings)

    unknown_user = FakeUser(
        id=uuid4(),
        email="unknown@example.com",
        password_hash=hash_password("strong-password"),
        full_name=None,
    )
    user_repository.users_by_id[unknown_user.id] = unknown_user
    user_repository.users_by_email[unknown_user.email] = unknown_user

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "strong-password",
        },
    )
    access_token = login_response.json()["access_token"]

    user_repository.users_by_id.clear()
    user_repository.users_by_email.clear()

    response = client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 401


def test_refresh_returns_new_token_pair_and_revokes_old_refresh_token(
    test_settings: Settings,
) -> None:
    client, _, refresh_session_repository = make_auth_client(test_settings)

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )
    old_refresh_token = login_response.json()["refresh_token"]

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )

    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]
    assert refresh_response.json()["refresh_token"]
    assert refresh_response.json()["refresh_token"] != old_refresh_token
    assert len(refresh_session_repository.sessions_by_jti_hash) == 2

    second_refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )

    assert second_refresh_response.status_code == 401


def test_logout_revokes_refresh_token(test_settings: Settings) -> None:
    client, _, _ = make_auth_client(test_settings)

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    logout_response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert logout_response.status_code == 200
    assert logout_response.json() == {"status": "ok"}
    assert refresh_response.status_code == 401
