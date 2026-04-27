import pytest
from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        app_name="Test API",
        app_env="test",
        api_v1_prefix="/api/v1",
        cors_origins="https://psihologpashkov.ru,https://www.psihologpashkov.ru",
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/test",
        jwt_access_secret="test-access-secret",
        jwt_refresh_secret="test-refresh-secret",
        jwt_access_ttl_minutes=15,
        jwt_refresh_ttl_days=30,
        cache_default_ttl_seconds=300,
        enable_openapi=True,
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    app = create_app(test_settings)
    return TestClient(app)
