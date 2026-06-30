"""FastAPI application entry point."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from fifa26_engine.api.accuracy_mappers import (
    evaluated_fixture_to_response,
    report_to_summary_response,
    summary_to_response,
)
from fifa26_engine.api.deps import (
    AppState,
    get_accuracy_service,
    get_app_state,
    get_prediction_service,
    lifespan,
)
from fifa26_engine.api.mappers import breakdown_to_prediction_response, fixture_to_response
from fifa26_engine.api.schemas import (
    AccuracyFixturesListResponse,
    AccuracyRecomputeResponse,
    AccuracySummaryResponse,
    FixturesListResponse,
    ModelInfoResponse,
    PredictionResponse,
    StatusResponse,
    TeamStatsListResponse,
    TeamTournamentStatsResponse,
)
from fifa26_engine.data.provider import Fixture
from fifa26_engine.data.stadiums import enrich_fixture, resolve_stadium
from fifa26_engine.data.team_metrics import compute_all_team_stats
from fifa26_engine.data.wc2026_store import WC2026Store
from fifa26_engine.models.temporal import resolve_as_of_utc
from fifa26_engine.services.accuracy_service import AccuracyService
from fifa26_engine.services.prediction_service import PredictionService
from fifa26_engine.services.refresh_service import _cache_key, load_fixtures_into_cache
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


@app.get("/status", response_model=StatusResponse)
async def system_status(request: Request) -> StatusResponse:
    """Return background refresh timestamps and fixture counts."""
    state = get_app_state(request)
    metadata = (
        state.refresh_service.metadata
        if state.refresh_service is not None
        else None
    )
    return StatusResponse(
        last_fixture_refresh_utc=metadata.last_fixture_refresh_utc if metadata else None,
        last_prediction_cache_clear_utc=(
            metadata.last_prediction_cache_clear_utc if metadata else None
        ),
        provider_mode=state.provider_mode,  # type: ignore[arg-type]
        fixture_counts=metadata.fixture_counts if metadata else {},
        refresh_interval_seconds=state.settings.refresh_interval_seconds,
        refresh_enabled=state.settings.refresh_enabled,
        last_refresh_error=metadata.last_refresh_error if metadata else None,
        ledger_prediction_count=state.prediction_store.count_predictions(),
    )


@app.get("/model/info", response_model=ModelInfoResponse)
async def model_info(
    service: PredictionService = Depends(get_prediction_service),
) -> ModelInfoResponse:
    """Return active model hyperparameters and version for UI display."""
    config = service.model_config
    return ModelInfoResponse(
        model_version=config.model_version,
        team_history_limit=config.team_history_limit,
        shrinkage_prior_matches=config.shrinkage_prior_matches,
        dixon_coles_rho=config.dixon_coles_rho,
        weather_delta_scale=config.weather_delta_scale,
        weather_min_bucket_samples=config.weather_min_bucket_samples,
        intercept_prior_goals=config.intercept_prior_goals,
        time_decay_half_life_days=config.time_decay_half_life_days,
        tournament_min_total_xg=config.tournament_min_total_xg,
        elo_blend_weight=config.elo_blend_weight,
        host_nation_boost=config.host_nation_boost,
    )


@app.get("/teams/stats", response_model=TeamStatsListResponse)
async def team_tournament_stats(
    request: Request,
    team_id: str | None = Query(default=None, description="Filter to one team slug"),
) -> TeamStatsListResponse:
    """Return WC 2026 tournament stats for each national team (openfootball data)."""
    state = get_app_state(request)
    provider = state.prediction_service.provider
    if not hasattr(provider, "_store"):
        raise HTTPException(
            status_code=400,
            detail="Team stats require DATA_PROVIDER=openfootball.",
        )
    store: WC2026Store = provider._store  # type: ignore[attr-defined]
    store.ensure_loaded()
    stats = compute_all_team_stats(store)
    if team_id is not None:
        stats = [item for item in stats if item.team_id == team_id]
        if not stats:
            raise HTTPException(status_code=404, detail=f"Team not found: {team_id}")
    return TeamStatsListResponse(
        source="openfootball",
        competition="FIFA World Cup 2026",
        fixture_count=len(store.fixtures),
        finished_count=sum(1 for fixture in store.fixtures if fixture.status == "finished"),
        teams=[TeamTournamentStatsResponse(**item.to_dict()) for item in stats],
    )


@app.get("/accuracy/summary", response_model=AccuracySummaryResponse)
async def accuracy_summary(
    request: Request,
    accuracy_service: AccuracyService = Depends(get_accuracy_service),
) -> AccuracySummaryResponse:
    """Return aggregate accuracy metrics from the stored prediction ledger."""
    summary = await accuracy_service.get_summary()
    return summary_to_response(summary)


@app.get("/accuracy/fixtures", response_model=AccuracyFixturesListResponse)
async def accuracy_fixtures(
    request: Request,
    accuracy_service: AccuracyService = Depends(get_accuracy_service),
    limit: int = Query(default=50, ge=1, le=500),
) -> AccuracyFixturesListResponse:
    """Return per-fixture stored predictions vs actual finished results."""
    items = await accuracy_service.get_fixture_evaluations(limit=limit)
    report = accuracy_service.cached_report
    computed_at = report.computed_at if report else datetime.now(timezone.utc)
    return AccuracyFixturesListResponse(
        items=[evaluated_fixture_to_response(item) for item in items],
        computed_at=computed_at,
    )


@app.post("/accuracy/recompute", response_model=AccuracyRecomputeResponse)
async def accuracy_recompute(
    request: Request,
    accuracy_service: AccuracyService = Depends(get_accuracy_service),
    service: PredictionService = Depends(get_prediction_service),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> AccuracyRecomputeResponse:
    """Recompute accuracy metrics from the ledger (does not refit models)."""
    state = get_app_state(request)
    admin_key = state.settings.accuracy_admin_key
    if admin_key and x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Key")

    fixtures = await service.provider.get_fixtures(limit=500)
    report = await accuracy_service.recompute(fixtures)
    return AccuracyRecomputeResponse(
        summary=report_to_summary_response(report),
        evaluated_count=len(report.fixtures),
    )


async def _fetch_fixtures(
    state: AppState,
    service: PredictionService,
    status: str | None,
    limit: int,
    *,
    force_refresh: bool = False,
) -> FixturesListResponse:
    cache_key = _cache_key(status, limit)
    if not force_refresh:
        cached = state.fixtures_cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

    if force_refresh:
        state.invalidate_fixture_caches()

    return await load_fixtures_into_cache(state, status, limit)


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
    if state.refresh_service is not None:
        await state.refresh_service.refresh_all()
        cache_key = _cache_key(status, limit)
        cached = state.fixtures_cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]
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
        model_version=service.model_config.model_version,
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
