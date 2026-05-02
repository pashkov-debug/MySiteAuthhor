from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EmailVerificationToken


class SQLAlchemyEmailVerificationTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> EmailVerificationToken:
        verification_token = EmailVerificationToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(verification_token)

        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise

        await self._session.refresh(verification_token)

        return verification_token

    async def get_by_token_hash(self, token_hash: str) -> EmailVerificationToken | None:
        result = await self._session.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def mark_used(self, token_id: UUID, used_at: datetime | None = None) -> bool:
        verification_token = await self._session.get(EmailVerificationToken, token_id)

        if verification_token is None:
            return False

        if verification_token.used_at is None:
            verification_token.used_at = used_at or datetime.now(UTC)
            await self._session.commit()
            await self._session.refresh(verification_token)

        return True

    async def mark_unused_for_user_used(self, user_id: UUID, used_at: datetime | None = None) -> int:
        result = await self._session.execute(
            update(EmailVerificationToken)
            .where(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.used_at.is_(None),
            )
            .values(used_at=used_at or datetime.now(UTC))
        )
        await self._session.commit()

        return result.rowcount or 0
