from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RefreshSession


class SQLAlchemyRefreshSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(
        self,
        user_id: UUID,
        jti_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> RefreshSession:
        refresh_session = RefreshSession(
            user_id=user_id,
            jti_hash=jti_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self._session.add(refresh_session)

        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise

        await self._session.refresh(refresh_session)

        return refresh_session

    async def get_by_jti_hash(self, jti_hash: str) -> RefreshSession | None:
        result = await self._session.execute(
            select(RefreshSession).where(RefreshSession.jti_hash == jti_hash)
        )
        return result.scalar_one_or_none()

    async def revoke_by_jti_hash(self, jti_hash: str) -> bool:
        refresh_session = await self.get_by_jti_hash(jti_hash)

        if refresh_session is None:
            return False

        if refresh_session.revoked_at is None:
            refresh_session.revoked_at = datetime.now(UTC)
            await self._session.commit()
            await self._session.refresh(refresh_session)

        return True

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        result = await self._session.execute(
            update(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.commit()

        return result.rowcount or 0
