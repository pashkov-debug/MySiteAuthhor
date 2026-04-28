import hashlib
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.core.config import Settings, get_settings
from app.core.jwt import ExpiredTokenError, InvalidTokenError, TokenPayload, decode_token
from app.services.auth_service import (
    AuthTokenPair,
    InactiveUserError,
    UserRepository,
    create_token_pair,
)


class RefreshSessionError(Exception):
    pass


class InvalidRefreshTokenError(RefreshSessionError):
    pass


class InvalidRefreshSessionError(RefreshSessionError):
    pass


class RefreshSessionForAuth(Protocol):
    id: UUID
    user_id: UUID
    jti_hash: str
    expires_at: datetime
    revoked_at: datetime | None


class RefreshSessionRepository(Protocol):
    async def create_session(
        self,
        user_id: UUID,
        jti_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> RefreshSessionForAuth:
        pass

    async def get_by_jti_hash(self, jti_hash: str) -> RefreshSessionForAuth | None:
        pass

    async def revoke_by_jti_hash(self, jti_hash: str) -> bool:
        pass

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        pass


def hash_jti(jti: str) -> str:
    if not jti:
        raise ValueError("JTI must not be empty")

    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


def decode_refresh_token(
    refresh_token: str,
    settings: Settings | None = None,
) -> TokenPayload:
    app_settings = settings or get_settings()

    try:
        return decode_token(
            refresh_token,
            expected_type="refresh",
            settings=app_settings,
        )
    except (ExpiredTokenError, InvalidTokenError) as exc:
        raise InvalidRefreshTokenError("Refresh token is invalid") from exc


async def store_refresh_token(
    refresh_token: str,
    refresh_session_repository: RefreshSessionRepository,
    settings: Settings | None = None,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> RefreshSessionForAuth:
    payload = decode_refresh_token(refresh_token, settings)

    try:
        user_id = UUID(payload.sub)
    except ValueError as exc:
        raise InvalidRefreshTokenError("Refresh token subject is invalid") from exc

    expires_at = datetime.fromtimestamp(payload.exp, tz=UTC)

    return await refresh_session_repository.create_session(
        user_id=user_id,
        jti_hash=hash_jti(payload.jti),
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )


async def refresh_token_pair(
    refresh_token: str,
    user_repository: UserRepository,
    refresh_session_repository: RefreshSessionRepository,
    settings: Settings | None = None,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> AuthTokenPair:
    app_settings = settings or get_settings()
    payload = decode_refresh_token(refresh_token, app_settings)
    jti_hash = hash_jti(payload.jti)

    refresh_session = await refresh_session_repository.get_by_jti_hash(jti_hash)

    if refresh_session is None:
        raise InvalidRefreshSessionError("Refresh session not found")

    if refresh_session.revoked_at is not None:
        raise InvalidRefreshSessionError("Refresh session is revoked")

    if is_expired(refresh_session.expires_at):
        raise InvalidRefreshSessionError("Refresh session has expired")

    try:
        user_id = UUID(payload.sub)
    except ValueError as exc:
        raise InvalidRefreshTokenError("Refresh token subject is invalid") from exc

    if refresh_session.user_id != user_id:
        raise InvalidRefreshSessionError("Refresh session user mismatch")

    user = await user_repository.get_by_id(user_id)

    if user is None:
        raise InvalidRefreshSessionError("User not found")

    if not user.is_active:
        raise InactiveUserError("User is inactive")

    token_pair = create_token_pair(user.id, app_settings)

    await refresh_session_repository.revoke_by_jti_hash(jti_hash)
    await store_refresh_token(
        refresh_token=token_pair.refresh_token,
        refresh_session_repository=refresh_session_repository,
        settings=app_settings,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    return token_pair


async def logout_refresh_token(
    refresh_token: str,
    refresh_session_repository: RefreshSessionRepository,
    settings: Settings | None = None,
) -> bool:
    try:
        payload = decode_refresh_token(refresh_token, settings)
    except InvalidRefreshTokenError:
        return False

    return await refresh_session_repository.revoke_by_jti_hash(hash_jti(payload.jti))


def is_expired(expires_at: datetime) -> bool:
    normalized_expires_at = expires_at

    if normalized_expires_at.tzinfo is None:
        normalized_expires_at = normalized_expires_at.replace(tzinfo=UTC)

    return normalized_expires_at <= datetime.now(UTC)
