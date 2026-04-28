from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.api.deps import get_refresh_session_repository, get_user_repository
from app.core.config import Settings
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

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        revoked_count = 0

        for refresh_session in self.sessions_by_jti_hash.values():
            if refresh_session.user_id == user_id and refresh_session.revoked_at is None:
                refresh_session.revoked_at = datetime.now(UTC)
                revoked_count += 1

        return revoked_count


def make_cookie_client(
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


def register_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )

    assert response.status_code == 201


def login_user(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )

    assert response.status_code == 200

    return response.json()


def test_login_sets_http_only_refresh_cookie(test_settings: Settings) -> None:
    client, _, _ = make_cookie_client(test_settings)

    register_user(client)
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )

    assert response.status_code == 200
    assert test_settings.auth_refresh_cookie_name in response.cookies
    assert "httponly" in response.headers["set-cookie"].lower()


def test_refresh_accepts_refresh_token_from_cookie(test_settings: Settings) -> None:
    client, _, _ = make_cookie_client(test_settings)

    register_user(client)
    old_token_pair = login_user(client)

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    body = response.json()

    assert body["access_token"]
    assert body["refresh_token"]
    assert body["refresh_token"] != old_token_pair["refresh_token"]


def test_refresh_prefers_body_token_over_cookie(test_settings: Settings) -> None:
    client, _, _ = make_cookie_client(test_settings)

    register_user(client)
    first_token_pair = login_user(client)

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_token_pair["refresh_token"]},
    )

    assert response.status_code == 200
    assert response.json()["refresh_token"] != first_token_pair["refresh_token"]


def test_refresh_without_body_or_cookie_returns_401(test_settings: Settings) -> None:
    client, _, _ = make_cookie_client(test_settings)

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 401


def test_logout_accepts_refresh_token_from_cookie_and_clears_cookie(
    test_settings: Settings,
) -> None:
    client, _, _ = make_cookie_client(test_settings)

    register_user(client)
    login_user(client)

    logout_response = client.post("/api/v1/auth/logout")
    refresh_response = client.post("/api/v1/auth/refresh")

    assert logout_response.status_code == 200
    assert logout_response.json() == {"status": "ok"}
    assert refresh_response.status_code == 401
    assert "max-age=0" in logout_response.headers["set-cookie"].lower()
