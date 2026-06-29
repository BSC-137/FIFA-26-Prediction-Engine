"""Tests for background fixture refresh service."""

from __future__ import annotations

import pytest

from fifa26_engine.api.deps import build_app_state
from fifa26_engine.config import Settings
from fifa26_engine.data.mock_provider import MockFixtureProvider
from fifa26_engine.services.prediction_service import PredictionService
from fifa26_engine.services.refresh_service import FixtureRefreshService, _cache_key


@pytest.fixture
def refresh_service() -> FixtureRefreshService:
    settings = Settings(use_mock_data=True, refresh_enabled=False)
    state = build_app_state(settings)
    state.prediction_service = PredictionService(
        provider=MockFixtureProvider(),
        settings=settings,
    )
    return FixtureRefreshService(state, limit=100)


@pytest.mark.asyncio
async def test_refresh_all_warms_status_caches(refresh_service: FixtureRefreshService) -> None:
    await refresh_service.refresh_all()
    state = refresh_service._state
    metadata = refresh_service.metadata

    assert metadata.last_fixture_refresh_utc is not None
    assert metadata.last_prediction_cache_clear_utc is not None
    assert metadata.fixture_counts["scheduled"] > 0
    assert metadata.fixture_counts["finished"] > 0
    assert state.fixtures_cache.get(_cache_key("scheduled", 100)) is not None
    assert state.fixtures_cache.get(_cache_key("live", 100)) is not None
    assert state.fixtures_cache.get(_cache_key("finished", 100)) is not None


@pytest.mark.asyncio
async def test_refresh_handles_provider_failure_gracefully() -> None:
    class FailingProvider:
        async def get_fixtures(self, status: str | None = None, limit: int = 100) -> list:
            raise ConnectionError("provider down")

        async def get_team_results(self, team_id: str, limit: int = 30) -> list:
            return []

        async def get_fixture_by_id(self, fixture_id: str):
            return None

    settings = Settings(use_mock_data=True)
    state = build_app_state(settings)
    state.prediction_service = PredictionService(provider=FailingProvider(), settings=settings)
    service = FixtureRefreshService(state)

    await service.refresh_all()
    assert service.metadata.last_refresh_error is not None
