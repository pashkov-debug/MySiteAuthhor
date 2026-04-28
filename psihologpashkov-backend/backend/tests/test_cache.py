import pytest
from app.services.cache import InMemoryCache


async def test_cache_set_and_get_value() -> None:
    cache = InMemoryCache(default_ttl_seconds=300)

    await cache.set("user:1", {"id": 1})

    assert await cache.get("user:1") == {"id": 1}


async def test_cache_returns_none_for_missing_key() -> None:
    cache = InMemoryCache(default_ttl_seconds=300)

    assert await cache.get("missing") is None


async def test_cache_deletes_value() -> None:
    cache = InMemoryCache(default_ttl_seconds=300)

    await cache.set("user:1", "value")

    assert await cache.delete("user:1")
    assert not await cache.delete("user:1")
    assert await cache.get("user:1") is None


async def test_cache_expires_value_by_ttl() -> None:
    now = 1_000.0
    cache = InMemoryCache(default_ttl_seconds=300, clock=lambda: now)

    await cache.set("user:1", "value", ttl_seconds=10)

    assert await cache.get("user:1") == "value"

    now = 1_011.0

    assert await cache.get("user:1") is None


async def test_cache_does_not_store_value_with_zero_ttl() -> None:
    cache = InMemoryCache(default_ttl_seconds=300)

    await cache.set("user:1", "value", ttl_seconds=0)

    assert await cache.get("user:1") is None


async def test_cache_rejects_empty_key() -> None:
    cache = InMemoryCache(default_ttl_seconds=300)

    with pytest.raises(ValueError, match="Cache key must not be empty"):
        await cache.get("")
