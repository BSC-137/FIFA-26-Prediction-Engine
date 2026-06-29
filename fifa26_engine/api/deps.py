"""FastAPI dependency injection and application lifecycle."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import FastAPI, Request

from fifa26_engine.config import Settings, get_settings
from fifa26_engine.data.weather_provider import create_weather_provider
from fifa26_engine.services.prediction_service import PredictionService, create_fixture_provider
from fifa26_engine.services.refresh_service import FixtureRefreshService
from fifa26_engine.utils.cache import TTLCache
from fifa26_engine.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


@dataclass
class AppState:
    """Shared application state for the API process."""

    settings: Settings
    prediction_service: PredictionService
    fixtures_cache: TTLCache[str, object] = field(default_factory=TTLCache)
    predictions_cache: TTLCache[str, object] = field(default_factory=TTLCache)
    refresh_service: FixtureRefreshService | None = None
    _refresh_stop: asyncio.Event | None = field(default=None, repr=False)
    _refresh_task: asyncio.Task[None] | None = field(default=None, repr=False)

    @property
    def data_source(self) -> str:
        if self.settings.effective_use_mock_data:
            return "mock"
        return "api-football"

    @property
    def provider_mode(self) -> str:
        return "mock" if self.settings.effective_use_mock_data else "api"

    def invalidate_fixture_caches(self) -> None:
        """Clear API fixture caches and underlying provider cache."""
        self.fixtures_cache.clear()
        provider = self.prediction_service.provider
        if hasattr(provider, "clear_cache"):
            provider.clear_cache()  # type: ignore[operator]
        logger.info("Fixture caches invalidated")

    def invalidate_prediction_caches(self) -> None:
        """Clear API prediction caches and record timestamp."""
        self.predictions_cache.clear()
        if self.refresh_service is not None:
            self.refresh_service.metadata.last_prediction_cache_clear_utc = datetime.now(
                timezone.utc,
            )
        logger.info("Prediction caches invalidated")

    async def shutdown(self) -> None:
        """Stop background refresh and close HTTP clients."""
        if self._refresh_stop is not None:
            self._refresh_stop.set()
        if self._refresh_task is not None:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

        provider = self.prediction_service.provider
        if hasattr(provider, "close"):
            await provider.close()  # type: ignore[operator]
        weather_provider = self.prediction_service._weather_provider
        if hasattr(weather_provider, "close"):
            await weather_provider.close()  # type: ignore[operator]


def build_app_state(settings: Settings | None = None) -> AppState:
    """Construct application state with configured services."""
    resolved = settings or get_settings()
    configure_logging(resolved.log_level)
    weather_provider = create_weather_provider(resolved)
    service = PredictionService(
        provider=create_fixture_provider(resolved),
        settings=resolved,
        weather_provider=weather_provider,
    )
    state = AppState(
        settings=resolved,
        prediction_service=service,
        fixtures_cache=TTLCache(default_ttl_seconds=resolved.fixtures_cache_ttl_seconds),
        predictions_cache=TTLCache(default_ttl_seconds=resolved.predictions_cache_ttl_seconds),
    )
    state.refresh_service = FixtureRefreshService(state)
    return state


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup and graceful shutdown of shared resources."""
    if not hasattr(app.state, "app_state"):
        app.state.app_state = build_app_state()

    state: AppState = app.state.app_state
    if state.settings.refresh_enabled:
        stop_event = asyncio.Event()
        state._refresh_stop = stop_event
        state._refresh_task = await state.refresh_service.start(stop_event)  # type: ignore[union-attr]
        logger.info(
            "Background fixture refresh enabled (interval=%ss)",
            state.settings.refresh_interval_seconds,
        )
    else:
        logger.info("Background fixture refresh disabled")

    yield
    await state.shutdown()


def get_app_state(request: Request) -> AppState:
    """Return shared application state from the request."""
    return request.app.state.app_state


def get_settings_dep(request: Request) -> Settings:
    """FastAPI dependency for application settings."""
    return request.app.state.app_state.settings


def get_prediction_service(request: Request) -> PredictionService:
    """FastAPI dependency for the prediction service."""
    return request.app.state.app_state.prediction_service
