"""FastAPI application entry point."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from fifa26_engine.api.deps import (
    AppState,
    build_app_state,
    get_app_state,
    get_prediction_service,
    lifespan,
)
from fifa26_engine.api.mappers import breakdown_to_prediction_response, fixture_to_response
from fifa26_engine.api.schemas import FixturesListResponse, PredictionResponse
from fifa26_engine.data.provider import Fixture
from fifa26_engine.data.stadiums import enrich_fixture, resolve_stadium
from fifa26_engine.models.temporal import resolve_as_of_utc
from fifa26_engine.services.prediction_service import PredictionService
from fifa26_engine.utils.logging import configure_logging

configure_logging()

app = FastAPI(
    title="FIFA 26 Prediction Engine",
    description="World Cup 2026 match prediction API with weather & pitch adjustments",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check(request: Request) -> dict[str, str]:
    """Liveness probe for deployments."""
    state: AppState = get_app_state(request)
    return {"status": "ok", "source": state.data_source}


async def _fetch_fixtures(
    state: AppState,
    service: PredictionService,
    status: str | None,
    limit: int,
    *,
    force_refresh: bool = False,
) -> FixturesListResponse:
    cache_key = f"fixtures:{status}:{limit}"
    if not force_refresh:
        cached = state.fixtures_cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

    if force_refresh:
        state.invalidate_fixture_caches()

    fixtures = await service.provider.get_fixtures(status=status, limit=limit)
    refreshed_at = datetime.now(timezone.utc)
    response = FixturesListResponse(
        items=[fixture_to_response(fixture) for fixture in fixtures],
        refreshed_at=refreshed_at,
        source=state.data_source,
    )
    state.fixtures_cache.set(
        cache_key,
        response,
        ttl=state.settings.fixtures_cache_ttl_seconds,
    )
    return response


@app.get("/fixtures", response_model=FixturesListResponse)
async def list_fixtures(
    request: Request,
    service: PredictionService = Depends(get_prediction_service),
    status: Literal["scheduled", "live", "finished"] | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> FixturesListResponse:
    """List World Cup fixtures, optionally filtered by status."""
    state = get_app_state(request)
    return await _fetch_fixtures(state, service, status, limit)


@app.get("/fixtures/refresh", response_model=FixturesListResponse)
async def refresh_fixtures(
    request: Request,
    service: PredictionService = Depends(get_prediction_service),
    status: Literal["scheduled", "live", "finished"] | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> FixturesListResponse:
    """Bust fixture caches and return a freshly loaded fixture list."""
    state = get_app_state(request)
    state.invalidate_prediction_caches()
    return await _fetch_fixtures(state, service, status, limit, force_refresh=True)


async def _predict_fixture(
    state: AppState,
    service: PredictionService,
    fixture: Fixture,
    cache_key: str,
) -> PredictionResponse:
    cached = state.predictions_cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    enriched = enrich_fixture(fixture)
    as_of = resolve_as_of_utc(enriched.kickoff_utc, enriched.status, None)
    breakdown = await service.predict_fixture_markets(enriched, as_of_utc=as_of)
    stadium = resolve_stadium(enriched)
    pitch = stadium.pitch_type

    response = breakdown_to_prediction_response(
        enriched,
        breakdown,
        as_of_utc=as_of,
        pitch_type=pitch,
    )
    state.predictions_cache.set(
        cache_key,
        response,
        ttl=state.settings.predictions_cache_ttl_seconds,
    )
    return response


@app.get("/predict/{fixture_id}", response_model=PredictionResponse)
async def predict_by_fixture_id(
    fixture_id: str,
    request: Request,
    service: PredictionService = Depends(get_prediction_service),
) -> PredictionResponse:
    """Predict markets for a known fixture ID."""
    state = get_app_state(request)
    fixture = await service.get_fixture(fixture_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail=f"Fixture not found: {fixture_id}")
    return await _predict_fixture(state, service, fixture, f"predict:fixture:{fixture_id}")


@app.get("/predict", response_model=PredictionResponse)
async def predict_manual_matchup(
    request: Request,
    service: PredictionService = Depends(get_prediction_service),
    home_team_id: str = Query(..., min_length=1),
    away_team_id: str = Query(..., min_length=1),
    kickoff_utc: datetime = Query(...),
    home_team_name: str | None = Query(default=None),
    away_team_name: str | None = Query(default=None),
    venue: str | None = Query(default=None),
    stage: str = Query(default="Manual"),
) -> PredictionResponse:
    """Predict markets for a manual team matchup (no stored fixture required)."""
    state = get_app_state(request)
    fixture = enrich_fixture(
        Fixture(
            fixture_id=f"manual-{home_team_id}-{away_team_id}-{kickoff_utc.isoformat()}",
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_team_name=home_team_name or home_team_id,
            away_team_name=away_team_name or away_team_id,
            kickoff_utc=kickoff_utc,
            status="scheduled",
            competition="FIFA World Cup 2026",
            stage=stage,
            venue=venue,
            home_goals=None,
            away_goals=None,
        ),
    )
    cache_key = (
        f"predict:manual:{home_team_id}:{away_team_id}:{kickoff_utc.isoformat()}:{venue}"
    )
    return await _predict_fixture(state, service, fixture, cache_key)
