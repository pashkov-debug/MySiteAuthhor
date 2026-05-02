from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

from app.api.deps import (
    get_email_sender,
    get_email_verification_token_repository,
    get_refresh_session_repository,
    get_user_repository,
)
from app.core.config import Settings
from app.core.email import OutgoingEmail
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
    email_verified_at: datetime | None = None
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
        self.users_by_email[email] = user

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




@dataclass(slots=True)
class FakeEmailVerificationToken:
    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    used_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class FakeEmailVerificationTokenRepository:
    tokens_by_hash: dict[str, FakeEmailVerificationToken] = field(default_factory=dict)

    async def create_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> FakeEmailVerificationToken:
        token = FakeEmailVerificationToken(
            id=uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.tokens_by_hash[token_hash] = token

        return token

    async def get_by_token_hash(self, token_hash: str) -> FakeEmailVerificationToken | None:
        return self.tokens_by_hash.get(token_hash)

    async def mark_used(self, token_id: UUID, used_at: datetime | None = None) -> bool:
        for token in self.tokens_by_hash.values():
            if token.id == token_id:
                token.used_at = used_at or datetime.now(UTC)
                return True

        return False

    async def mark_unused_for_user_used(
        self,
        user_id: UUID,
        used_at: datetime | None = None,
    ) -> int:
        marked_count = 0

        for token in self.tokens_by_hash.values():
            if token.user_id == user_id and token.used_at is None:
                token.used_at = used_at or datetime.now(UTC)
                marked_count += 1

        return marked_count


@dataclass(slots=True)
class CapturingEmailSender:
    messages: list[OutgoingEmail] = field(default_factory=list)

    async def send(self, message: OutgoingEmail) -> None:
        self.messages.append(message)


def get_last_email_token(client: TestClient) -> str:
    email_sender = client.email_sender
    message = email_sender.messages[-1]
    link = message.text_body.split("http", 1)[1].split("\n", 1)[0]
    parsed = urlsplit(f"http{link}")

    return parse_qs(parsed.query)["token"][0]


def verify_registered_email(client: TestClient) -> None:
    token = get_last_email_token(client)
    response = client.get(f"/api/v1/auth/verify-email?token={token}")

    assert response.status_code == 200


def make_auth_client(
    test_settings: Settings,
) -> tuple[TestClient, FakeUserRepository, FakeRefreshSessionRepository]:
    app = create_app(test_settings)
    user_repository = FakeUserRepository()
    refresh_session_repository = FakeRefreshSessionRepository()
    verification_token_repository = FakeEmailVerificationTokenRepository()
    email_sender = CapturingEmailSender()

    async def override_user_repository() -> FakeUserRepository:
        return user_repository

    async def override_refresh_session_repository() -> FakeRefreshSessionRepository:
        return refresh_session_repository

    async def override_email_verification_token_repository() -> FakeEmailVerificationTokenRepository:
        return verification_token_repository

    def override_email_sender() -> CapturingEmailSender:
        return email_sender

    app.dependency_overrides[get_user_repository] = override_user_repository
    app.dependency_overrides[get_refresh_session_repository] = override_refresh_session_repository
    app.dependency_overrides[get_email_verification_token_repository] = (
        override_email_verification_token_repository
    )
    app.dependency_overrides[get_email_sender] = override_email_sender

    client = TestClient(app)
    client.verification_token_repository = verification_token_repository
    client.email_sender = email_sender

    return client, user_repository, refresh_session_repository


def register_and_login(client: TestClient) -> str:
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )
    assert register_response.status_code == 201
    verify_registered_email(client)

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )

    return login_response.json()["access_token"]


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
    assert body["status"] == "email_verification_required"
    assert "password_hash" not in body


def test_register_blocks_login_until_email_is_verified(test_settings: Settings) -> None:
    client, _, _ = make_auth_client(test_settings)

    register_response = client.post(
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

    assert register_response.status_code == 201
    assert login_response.status_code == 403
    assert login_response.json()["detail"] == "Email is not verified"


def test_verify_email_activates_user(test_settings: Settings) -> None:
    client, user_repository, _ = make_auth_client(test_settings)

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )

    user = user_repository.users_by_email["user@example.com"]
    assert user.is_active is False
    assert user.email_verified_at is None

    verify_registered_email(client)

    assert user.is_active is True
    assert user.email_verified_at is not None


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

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )
    assert register_response.status_code == 201
    verify_registered_email(client)

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
    access_token = register_and_login(client)

    response = client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


def test_update_me_requires_authentication(test_settings: Settings) -> None:
    client, _, _ = make_auth_client(test_settings)

    response = client.patch(
        "/api/v1/me",
        json={"full_name": "Алексей"},
    )

    assert response.status_code == 401


def test_update_me_updates_current_user_profile(test_settings: Settings) -> None:
    client, _, _ = make_auth_client(test_settings)
    access_token = register_and_login(client)

    response = client.patch(
        "/api/v1/me",
        json={"full_name": "  Алексей Пашков  "},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"
    assert response.json()["full_name"] == "Алексей Пашков"


def test_update_me_can_clear_full_name(test_settings: Settings) -> None:
    client, _, _ = make_auth_client(test_settings)
    access_token = register_and_login(client)

    response = client.patch(
        "/api/v1/me",
        json={"full_name": "    "},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] is None


def test_me_rejects_inactive_user(test_settings: Settings) -> None:
    client, user_repository, _ = make_auth_client(test_settings)

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )
    assert register_response.status_code == 201
    verify_registered_email(client)

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

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )
    assert register_response.status_code == 201
    verify_registered_email(client)

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

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "strong-password",
        },
    )
    assert register_response.status_code == 201
    verify_registered_email(client)

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
