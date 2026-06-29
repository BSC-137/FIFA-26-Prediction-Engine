"""Background fixture cache refresh for live API data."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal

from fifa26_engine.api.mappers import fixture_to_response
from fifa26_engine.api.schemas import FixturesListResponse
from fifa26_engine.utils.logging import get_logger

if TYPE_CHECKING:
    from fifa26_engine.api.deps import AppState

logger = get_logger(__name__)

FixtureStatusKey = Literal["scheduled", "live", "finished"]
FIXTURE_STATUSES: tuple[FixtureStatusKey, ...] = ("scheduled", "live", "finished")
DEFAULT_REFRESH_LIMIT = 100


@dataclass
class RefreshMetadata:
    """Timestamps and counters from background refresh cycles."""

    last_fixture_refresh_utc: datetime | None = None
    last_prediction_cache_clear_utc: datetime | None = None
    last_refresh_error: str | None = None
    fixture_counts: dict[str, int] = field(
        default_factory=lambda: {"scheduled": 0, "live": 0, "finished": 0},
    )


def _cache_key(status: str | None, limit: int) -> str:
    return f"fixtures:{status}:{limit}"


def _build_list_response(
    state: AppState,
    fixtures: list,
    refreshed_at: datetime,
) -> FixturesListResponse:
    return FixturesListResponse(
        items=[fixture_to_response(fixture) for fixture in fixtures],
        refreshed_at=refreshed_at,
        source=state.data_source,
    )


def _store_fixture_cache(
    state: AppState,
    status: str | None,
    limit: int,
    response: FixturesListResponse,
) -> None:
    state.fixtures_cache.set(
        _cache_key(status, limit),
        response,
        ttl=state.settings.fixtures_cache_ttl_seconds,
    )


async def load_fixtures_into_cache(
    state: AppState,
    status: str | None,
    limit: int,
) -> FixturesListResponse:
    """Fetch fixtures from the provider and store them in the API cache."""
    fixtures = await state.prediction_service.provider.get_fixtures(status=status, limit=limit)
    refreshed_at = datetime.now(timezone.utc)
    response = _build_list_response(state, fixtures, refreshed_at)
    _store_fixture_cache(state, status, limit, response)
    return response


class FixtureRefreshService:
    """Periodically warms fixture caches for scheduled, live, and finished matches."""

    def __init__(self, state: AppState, *, limit: int = DEFAULT_REFRESH_LIMIT) -> None:
        self._state = state
        self._limit = limit
        self.metadata = RefreshMetadata()

    @property
    def interval_seconds(self) -> int:
        return self._state.settings.refresh_interval_seconds

    async def refresh_all(self) -> None:
        """Refresh all fixture status buckets and update metadata."""
        logger.info("Starting fixture cache refresh cycle")
        self._state.invalidate_fixture_caches()
        self._state.invalidate_prediction_caches()
        self.metadata.last_prediction_cache_clear_utc = datetime.now(timezone.utc)

        try:
            all_fixtures = await self._state.prediction_service.provider.get_fixtures(
                status=None,
                limit=self._limit,
            )
            refreshed_at = datetime.now(timezone.utc)
            counts = {status: 0 for status in FIXTURE_STATUSES}
            for fixture in all_fixtures:
                if fixture.status in counts:
                    counts[fixture.status] += 1

            _store_fixture_cache(
                self._state,
                None,
                self._limit,
                _build_list_response(self._state, all_fixtures, refreshed_at),
            )
            for status in FIXTURE_STATUSES:
                filtered = [fixture for fixture in all_fixtures if fixture.status == status]
                _store_fixture_cache(
                    self._state,
                    status,
                    self._limit,
                    _build_list_response(self._state, filtered, refreshed_at),
                )

            self.metadata.fixture_counts = counts
            self.metadata.last_fixture_refresh_utc = refreshed_at
            self.metadata.last_refresh_error = None
            logger.info(
                "Fixture cache refresh complete: scheduled=%s live=%s finished=%s",
                counts["scheduled"],
                counts["live"],
                counts["finished"],
            )

            if self._state.ledger_service is not None:
                try:
                    stored = await self._state.ledger_service.sync_ledger(all_fixtures)
                    logger.info("Ledger sync complete: %s new predictions stored", stored)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Ledger sync failed: %s", exc)
                    if self.metadata.last_refresh_error is None:
                        self.metadata.last_refresh_error = f"ledger: {exc}"

            try:
                await self._state.accuracy_service.recompute(all_fixtures)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Accuracy recompute failed: %s", exc)
        except Exception as exc:  # noqa: BLE001 — keep background loop alive
            self.metadata.last_refresh_error = str(exc)
            logger.exception("Fixture refresh cycle failed")

    async def run_periodic(self, stop_event: asyncio.Event) -> None:
        """Run ``refresh_all`` on a loop until ``stop_event`` is set."""
        while not stop_event.is_set():
            try:
                await self.refresh_all()
            except Exception as exc:  # noqa: BLE001
                self.metadata.last_refresh_error = str(exc)
                logger.exception("Unexpected fixture refresh cycle failure")

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self.interval_seconds)
                break
            except asyncio.TimeoutError:
                continue

    async def start(self, stop_event: asyncio.Event) -> asyncio.Task[None]:
        """Kick off periodic refresh and an immediate first cycle."""
        asyncio.create_task(self._safe_refresh("startup"))
        return asyncio.create_task(self.run_periodic(stop_event))

    async def _safe_refresh(self, reason: str) -> None:
        try:
            await self.refresh_all()
        except Exception as exc:  # noqa: BLE001
            self.metadata.last_refresh_error = str(exc)
            logger.exception("Fixture refresh failed during %s", reason)
