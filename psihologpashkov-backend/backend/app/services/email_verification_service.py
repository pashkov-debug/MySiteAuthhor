import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import urlencode, urlsplit, urlunsplit
from uuid import UUID

from app.core.config import Settings, get_settings
from app.core.email import EmailSender, OutgoingEmail
from app.services.auth_service import UserForAuth, UserRepository


class EmailVerificationError(Exception):
    pass


class InvalidEmailVerificationTokenError(EmailVerificationError):
    pass


class ExpiredEmailVerificationTokenError(EmailVerificationError):
    pass


class EmailAlreadyVerifiedError(EmailVerificationError):
    pass


class EmailVerificationTokenForAuth(Protocol):
    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    used_at: datetime | None


class EmailVerificationTokenRepository(Protocol):
    async def create_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> EmailVerificationTokenForAuth:
        pass

    async def get_by_token_hash(self, token_hash: str) -> EmailVerificationTokenForAuth | None:
        pass

    async def mark_used(self, token_id: UUID, used_at: datetime | None = None) -> bool:
        pass

    async def mark_unused_for_user_used(self, user_id: UUID, used_at: datetime | None = None) -> int:
        pass


@dataclass(frozen=True, slots=True)
class CreatedEmailVerificationToken:
    raw_token: str
    token_hash: str
    expires_at: datetime


def create_raw_email_verification_token(
    settings: Settings | None = None,
) -> CreatedEmailVerificationToken:
    app_settings = settings or get_settings()
    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(
        hours=app_settings.email_verification_token_ttl_hours
    )

    return CreatedEmailVerificationToken(
        raw_token=raw_token,
        token_hash=hash_email_verification_token(raw_token),
        expires_at=expires_at,
    )


def hash_email_verification_token(raw_token: str) -> str:
    if not raw_token or not raw_token.strip():
        raise ValueError("Email verification token must not be empty")

    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def build_email_verification_link(raw_token: str, settings: Settings | None = None) -> str:
    app_settings = settings or get_settings()
    base_url = app_settings.email_verification_link_base_url.strip()

    if "{token}" in base_url:
        return base_url.replace("{token}", raw_token)

    split_url = urlsplit(base_url)
    query = urlencode({"token": raw_token})

    return urlunsplit(
        (
            split_url.scheme,
            split_url.netloc,
            split_url.path,
            query if not split_url.query else f"{split_url.query}&{query}",
            split_url.fragment,
        )
    )


async def create_email_verification_token(
    user: UserForAuth,
    token_repository: EmailVerificationTokenRepository,
    settings: Settings | None = None,
) -> CreatedEmailVerificationToken:
    now = datetime.now(UTC)
    await token_repository.mark_unused_for_user_used(user.id, used_at=now)

    token = create_raw_email_verification_token(settings)
    await token_repository.create_token(
        user_id=user.id,
        token_hash=token.token_hash,
        expires_at=token.expires_at,
    )

    return token


async def send_registration_verification_email(
    user: UserForAuth,
    raw_token: str,
    email_sender: EmailSender,
    settings: Settings | None = None,
) -> None:
    app_settings = settings or get_settings()
    verification_link = build_email_verification_link(raw_token, app_settings)

    await email_sender.send(
        OutgoingEmail(
            to_email=user.email,
            subject="Подтвердите регистрацию",
            text_body=(
                "Здравствуйте!\n\n"
                "Для завершения регистрации перейдите по ссылке:\n"
                f"{verification_link}\n\n"
                "Если вы не регистрировались на сайте, просто проигнорируйте это письмо."
            ),
        )
    )


async def verify_email_by_token(
    raw_token: str,
    token_repository: EmailVerificationTokenRepository,
    user_repository: UserRepository,
) -> UserForAuth:
    token_hash = hash_email_verification_token(raw_token)
    verification_token = await token_repository.get_by_token_hash(token_hash)

    if verification_token is None:
        raise InvalidEmailVerificationTokenError("Email verification token is invalid")

    if verification_token.used_at is not None:
        raise InvalidEmailVerificationTokenError("Email verification token is already used")

    if is_expired(verification_token.expires_at):
        raise ExpiredEmailVerificationTokenError("Email verification token has expired")

    user = await user_repository.get_by_id(verification_token.user_id)

    if user is None:
        raise InvalidEmailVerificationTokenError("Email verification token user not found")

    if getattr(user, "email_verified_at", None) is not None and user.is_active:
        await token_repository.mark_used(verification_token.id)
        raise EmailAlreadyVerifiedError("Email is already verified")

    verified_user = await user_repository.mark_email_verified(user.id)

    if verified_user is None:
        raise InvalidEmailVerificationTokenError("Email verification token user not found")

    await token_repository.mark_used(verification_token.id)

    return verified_user


def is_expired(expires_at: datetime) -> bool:
    normalized_expires_at = expires_at

    if normalized_expires_at.tzinfo is None:
        normalized_expires_at = normalized_expires_at.replace(tzinfo=UTC)

    return normalized_expires_at <= datetime.now(UTC)
