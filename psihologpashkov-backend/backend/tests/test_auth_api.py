from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.api.deps import get_user_repository
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


def make_auth_client(test_settings: Settings) -> tuple[TestClient, FakeUserRepository]:
    app = create_app(test_settings)
    repository = FakeUserRepository()

    async def override_user_repository() -> FakeUserRepository:
        return repository

    app.dependency_overrides[get_user_repository] = override_user_repository

    return TestClient(app), repository


def test_register_creates_user(test_settings: Settings) -> None:
    client, _ = make_auth_client(test_settings)

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
    client, _ = make_auth_client(test_settings)
    payload = {
        "email": "user@example.com",
        "password": "strong-password",
    }

    first_response = client.post("/api/v1/auth/register", json=payload)
    second_response = client.post("/api/v1/auth/register", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_login_returns_token_pair(test_settings: Settings) -> None:
    client, _ = make_auth_client(test_settings)

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


def test_login_rejects_wrong_password(test_settings: Settings) -> None:
    client, _ = make_auth_client(test_settings)

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
    client, _ = make_auth_client(test_settings)

    response = client.get("/api/v1/me")

    assert response.status_code == 401


def test_me_returns_current_user(test_settings: Settings) -> None:
    client, _ = make_auth_client(test_settings)

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
    client, repository = make_auth_client(test_settings)

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )
    user = repository.users_by_email["user@example.com"]
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
    client, repository = make_auth_client(test_settings)

    unknown_user = FakeUser(
        id=uuid4(),
        email="unknown@example.com",
        password_hash=hash_password("strong-password"),
        full_name=None,
    )
    repository.users_by_id[unknown_user.id] = unknown_user
    repository.users_by_email[unknown_user.email] = unknown_user

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "strong-password",
        },
    )
    access_token = login_response.json()["access_token"]

    repository.users_by_id.clear()
    repository.users_by_email.clear()

    response = client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 401
