"""API-Football HTTP provider (stub implementation when no API key)."""

from __future__ import annotations

from typing import Optional

import httpx

from fifa26_engine.config import Settings, get_settings
from fifa26_engine.data.provider import FixtureRecord
from fifa26_engine.utils.cache import TTLCache
from fifa26_engine.utils.logging import get_logger

logger = get_logger(__name__)


class ApiFootballProvider:
    """Concrete ``FixtureProvider`` backed by the API-Football REST API."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[httpx.AsyncClient] = None,
        cache: Optional[TTLCache[str, list[FixtureRecord]]] = None,
    ) -> None:
        """Initialize the provider.

        Args:
            settings: Application settings; defaults to cached singleton.
            client: Optional shared HTTP client for testing or connection pooling.
            cache: Optional TTL cache for fixture list responses.
        """
        self._settings = settings or get_settings()
        self._client = client
        self._owns_client = client is None
        self._cache: TTLCache[str, list[FixtureRecord]] = cache or TTLCache(
            default_ttl_seconds=self._settings.cache_ttl_seconds,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._settings.api_football_base_url,
                headers={"x-apisports-key": self._settings.api_football_key},
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client if owned by this provider."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> ApiFootballProvider:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    def _cache_key(self, prefix: str, *parts: int | str) -> str:
        return f"{prefix}:" + ":".join(str(p) for p in parts)

    async def get_fixtures(
        self,
        competition_id: int,
        season: int,
    ) -> list[FixtureRecord]:
        """Fetch fixtures for a competition and season from API-Football."""
        cache_key = self._cache_key("fixtures", competition_id, season)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if not self._settings.has_api_key:
            logger.warning(
                "API_FOOTBALL_KEY not set; ApiFootballProvider returning empty fixture list.",
            )
            return []

        client = await self._get_client()
        response = await client.get(
            "/fixtures",
            params={"league": competition_id, "season": season},
        )
        response.raise_for_status()
        # TODO: map API-Football JSON payload to FixtureRecord instances.
        fixtures: list[FixtureRecord] = []
        self._cache.set(cache_key, fixtures)
        return fixtures

    async def get_fixture(self, fixture_id: int) -> Optional[FixtureRecord]:
        """Fetch a single fixture by ID from API-Football."""
        if not self._settings.has_api_key:
            logger.warning(
                "API_FOOTBALL_KEY not set; ApiFootballProvider cannot fetch fixture %s.",
                fixture_id,
            )
            return None

        client = await self._get_client()
        response = await client.get("/fixtures", params={"id": fixture_id})
        response.raise_for_status()
        # TODO: map API response to FixtureRecord.
        return None

    async def get_team_fixtures(
        self,
        team_id: int,
        season: int,
    ) -> list[FixtureRecord]:
        """Fetch fixtures for a team and season from API-Football."""
        cache_key = self._cache_key("team_fixtures", team_id, season)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if not self._settings.has_api_key:
            logger.warning(
                "API_FOOTBALL_KEY not set; ApiFootballProvider returning empty team fixtures.",
            )
            return []

        client = await self._get_client()
        response = await client.get(
            "/fixtures",
            params={"team": team_id, "season": season},
        )
        response.raise_for_status()
        # TODO: map API response to FixtureRecord list.
        fixtures: list[FixtureRecord] = []
        self._cache.set(cache_key, fixtures)
        return fixtures
