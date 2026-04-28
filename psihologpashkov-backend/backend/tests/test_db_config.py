from app.core.config import Settings
from app.db.session import create_db_engine, create_session_maker
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


async def test_create_db_engine_uses_configured_database_url(test_settings: Settings) -> None:
    engine = create_db_engine(test_settings)

    try:
        assert isinstance(engine, AsyncEngine)
        assert engine.sync_engine.url.drivername == "postgresql+asyncpg"
        assert engine.sync_engine.url.database == "test"
    finally:
        await engine.dispose()


async def test_create_session_maker_returns_async_session_factory(
    test_settings: Settings,
) -> None:
    engine = create_db_engine(test_settings)

    try:
        session_maker = create_session_maker(engine)

        assert isinstance(session_maker, async_sessionmaker)

        async with session_maker() as session:
            assert isinstance(session, AsyncSession)
    finally:
        await engine.dispose()
