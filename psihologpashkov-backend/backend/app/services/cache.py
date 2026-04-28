import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(slots=True)
class CacheItem:
    value: object
    expires_at: float | None


class InMemoryCache:
    def __init__(
        self,
        default_ttl_seconds: int = 300,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if default_ttl_seconds <= 0:
            raise ValueError("Default cache TTL must be positive")

        self.default_ttl_seconds = default_ttl_seconds
        self._clock = clock
        self._storage: dict[str, CacheItem] = {}

    async def get(self, key: str) -> object | None:
        self._validate_key(key)

        item = self._storage.get(key)
        if item is None:
            return None

        if self._is_expired(item):
            await self.delete(key)
            return None

        return item.value

    async def set(
        self,
        key: str,
        value: object,
        ttl_seconds: int | float | None = None,
    ) -> None:
        self._validate_key(key)

        effective_ttl = self.default_ttl_seconds if ttl_seconds is None else ttl_seconds

        if effective_ttl <= 0:
            await self.delete(key)
            return

        self._storage[key] = CacheItem(
            value=value,
            expires_at=self._clock() + effective_ttl,
        )

    async def delete(self, key: str) -> bool:
        self._validate_key(key)

        existed = key in self._storage
        self._storage.pop(key, None)

        return existed

    async def clear(self) -> None:
        self._storage.clear()

    def _is_expired(self, item: CacheItem) -> bool:
        if item.expires_at is None:
            return False

        return self._clock() >= item.expires_at

    @staticmethod
    def _validate_key(key: str) -> None:
        if not key or not key.strip():
            raise ValueError("Cache key must not be empty")
