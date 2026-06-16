"""Simple in-memory TTL cache."""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Generic, Optional, TypeVar

K = TypeVar("K")
V = TypeVar("V")


@dataclass
class _CacheEntry(Generic[V]):
    """Internal cache entry with expiration timestamp."""

    value: V
    expires_at: float


class TTLCache(Generic[K, V]):
    """Thread-safe in-memory cache with per-key time-to-live."""

    def __init__(self, default_ttl_seconds: int = 3600) -> None:
        """Initialize the cache.

        Args:
            default_ttl_seconds: Default TTL applied when ``set`` is called without ``ttl``.
        """
        self._default_ttl = max(0, default_ttl_seconds)
        self._store: dict[K, _CacheEntry[V]] = {}
        self._lock = Lock()

    def get(self, key: K) -> Optional[V]:
        """Return a cached value if present and not expired, else ``None``."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() >= entry.expires_at:
                del self._store[key]
                return None
            return entry.value

    def set(self, key: K, value: V, ttl: Optional[int] = None) -> None:
        """Store a value with an optional TTL override in seconds."""
        ttl_seconds = self._default_ttl if ttl is None else max(0, ttl)
        expires_at = time.monotonic() + ttl_seconds
        with self._lock:
            self._store[key] = _CacheEntry(value=value, expires_at=expires_at)

    def delete(self, key: K) -> None:
        """Remove a key from the cache if it exists."""
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """Remove all entries from the cache."""
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        """Return the number of entries currently stored (including expired)."""
        with self._lock:
            return len(self._store)
