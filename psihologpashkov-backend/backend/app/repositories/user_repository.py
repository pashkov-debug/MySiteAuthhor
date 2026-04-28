from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


class SQLAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        password_hash: str,
        full_name: str | None,
    ) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
        )
        self._session.add(user)

        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise

        await self._session.refresh(user)

        return user

    async def update_profile(
        self,
        user_id: UUID,
        full_name: str | None,
    ) -> User | None:
        user = await self.get_by_id(user_id)

        if user is None:
            return None

        user.full_name = full_name

        await self._session.commit()
        await self._session.refresh(user)

        return user

    async def update_password_hash(
        self,
        user_id: UUID,
        password_hash: str,
    ) -> User | None:
        user = await self.get_by_id(user_id)

        if user is None:
            return None

        user.password_hash = password_hash

        await self._session.commit()
        await self._session.refresh(user)

        return user
