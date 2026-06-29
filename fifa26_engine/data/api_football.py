"""API-Football HTTP provider with response mapping and resilient requests."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from fifa26_engine.config import ConfigError, Settings, get_settings
from fifa26_engine.data.mappers import map_api_fixture, map_api_fixture_to_match_result
from fifa26_engine.data.provider import Fixture, MatchResult
from fifa26_engine.utils.cache import TTLCache
from fifa26_engine.utils.logging import get_logger

logger = get_logger(__name__)

_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


class ApiFootballProvider:
    """Concrete ``FixtureProvider`` backed by the API-Football REST API."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
        cache: TTLCache[str, Any] | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            settings: Application settings; defaults to cached singleton.
            client: Optional shared HTTP client for testing or connection pooling.
            cache: Optional TTL cache for API responses.
        """
        self._settings = settings or get_settings()
        self._client = client
        self._owns_client = client is None
        self._cache: TTLCache[str, Any] = cache or TTLCache(
            default_ttl_seconds=self._settings.cache_ttl_seconds,
        )
        self._ensure_api_key()

    def _ensure_api_key(self) -> None:
        if not self._settings.has_api_key:
            raise ConfigError(
                "API_FOOTBALL_KEY is not configured. "
                "Set the key in .env or use MockFixtureProvider (USE_MOCK_DATA=true)."
            )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._settings.api_football_base_url,
                headers={"x-apisports-key": self._settings.api_football_key},
                timeout=self._settings.api_football_timeout_seconds,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client if owned by this provider."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def clear_cache(self) -> None:
        """Clear the internal response cache (used by /fixtures/refresh)."""
        self._cache.clear()

    async def __aenter__(self) -> ApiFootballProvider:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    def _cache_key(self, prefix: str, *parts: int | str) -> str:
        return f"{prefix}:" + ":".join(str(part) for part in parts)

    async def _request(
        self,
        path: str,
        params: dict[str, str | int],
    ) -> dict[str, Any]:
        """Perform a GET request with retries, logging, and error handling."""
        client = await self._get_client()
        max_retries = self._settings.api_football_max_retries
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(
                    "API-Football request",
                    extra={"path": path, "params": params, "attempt": attempt},
                )
                response = await client.get(path, params=params)
                if response.status_code in _RETRYABLE_STATUS_CODES and attempt < max_retries:
                    logger.warning(
                        "Retryable API-Football status %s for %s (attempt %s/%s)",
                        response.status_code,
                        path,
                        attempt,
                        max_retries,
                    )
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                response.raise_for_status()
                payload = response.json()
                errors = payload.get("errors")
                if errors:
                    logger.error("API-Football returned errors: %s", errors)
                    raise ConfigError(f"API-Football error response: {errors}")
                return payload
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(
                    "API-Football timeout for %s (attempt %s/%s)",
                    path,
                    attempt,
                    max_retries,
                )
            except httpx.TransportError as exc:
                last_error = exc
                logger.warning(
                    "API-Football transport error for %s (attempt %s/%s): %s",
                    path,
                    attempt,
                    max_retries,
                    exc,
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in _RETRYABLE_STATUS_CODES and attempt < max_retries:
                    last_error = exc
                    logger.warning(
                        "Retryable HTTP error %s for %s (attempt %s/%s)",
                        exc.response.status_code,
                        path,
                        attempt,
                        max_retries,
                    )
                else:
                    logger.error(
                        "API-Football HTTP error %s for %s",
                        exc.response.status_code,
                        path,
                    )
                    raise

            if attempt < max_retries:
                await asyncio.sleep(2 ** (attempt - 1))

        assert last_error is not None
        raise last_error

    def _map_fixtures(self, payload: dict[str, Any]) -> list[Fixture]:
        return [map_api_fixture(item) for item in payload.get("response", [])]

    def _map_team_results(self, payload: dict[str, Any]) -> list[MatchResult]:
        results: list[MatchResult] = []
        for item in payload.get("response", []):
            mapped = map_api_fixture_to_match_result(item)
            if mapped is not None:
                results.append(mapped)
        return results

    async def get_fixtures(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[Fixture]:
        """Fetch World Cup fixtures for the configured league and season."""
        cache_key = self._cache_key(
            "fixtures",
            self._settings.world_cup_league_id,
            self._settings.season,
            status or "all",
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            fixtures: list[Fixture] = cached
        else:
            payload = await self._request(
                "/fixtures",
                params={
                    "league": self._settings.world_cup_league_id,
                    "season": self._settings.season,
                },
            )
            fixtures = self._map_fixtures(payload)
            self._cache.set(cache_key, fixtures)
            logger.info(
                "Fetched %s fixtures for league=%s season=%s",
                len(fixtures),
                self._settings.world_cup_league_id,
                self._settings.season,
            )

        if status is not None:
            normalized = status.lower()
            fixtures = [fixture for fixture in fixtures if fixture.status == normalized]

        if limit <= 0:
            return []
        return fixtures[:limit]

    async def get_team_results(
        self,
        team_id: str,
        limit: int = 30,
    ) -> list[MatchResult]:
        """Fetch recent finished matches for a national team."""
        if limit <= 0:
            return []

        cache_key = self._cache_key("team_results", team_id, limit)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        payload = await self._request(
            "/fixtures",
            params={"team": team_id, "last": limit},
        )
        results = self._map_team_results(payload)
        results.sort(key=lambda match: match.date, reverse=True)
        self._cache.set(cache_key, results)
        logger.info("Fetched %s historical results for team_id=%s", len(results), team_id)
        return results[:limit]

    async def get_fixture_by_id(self, fixture_id: str) -> Fixture | None:
        """Fetch a single fixture by ID."""
        cache_key = self._cache_key("fixture", fixture_id)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        payload = await self._request("/fixtures", params={"id": fixture_id})
        items = payload.get("response", [])
        if not items:
            logger.info("Fixture not found: fixture_id=%s", fixture_id)
            return None

        fixture = map_api_fixture(items[0])
        self._cache.set(cache_key, fixture)
        return fixture
