"""Pydantic schemas for API request and response models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from fifa26_engine.config.model_config import DEFAULT_MODEL_VERSION

FixtureStatusSchema = Literal["scheduled", "live", "finished"]
PitchTypeSchema = Literal["grass", "hybrid", "artificial", "unknown"]
ProviderModeSchema = Literal["mock", "api"]
MODEL_VERSION = DEFAULT_MODEL_VERSION


class FixtureResponse(BaseModel):
    """Serialized fixture returned by the API."""

    fixture_id: str
    home_team_id: str
    away_team_id: str
    home_team_name: str
    away_team_name: str
    kickoff_utc: datetime
    status: FixtureStatusSchema
    competition: str
    stage: str
    venue: Optional[str] = None
    venue_city: Optional[str] = None
    venue_country: Optional[str] = None
    pitch_type: PitchTypeSchema = "unknown"
    home_goals: Optional[int] = Field(default=None, ge=0)
    away_goals: Optional[int] = Field(default=None, ge=0)


class MatchResultResponse(BaseModel):
    """Serialized historical match result."""

    match_id: str
    date: datetime
    home_team_id: str
    away_team_id: str
    home_goals: int = Field(ge=0)
    away_goals: int = Field(ge=0)
    is_neutral: bool
    competition: str


class PredictionProbabilities(BaseModel):
    """Match outcome probabilities (legacy 1X2 schema)."""

    home_win: float = Field(ge=0.0, le=1.0)
    draw: float = Field(ge=0.0, le=1.0)
    away_win: float = Field(ge=0.0, le=1.0)


class MatchPredictionResponse(BaseModel):
    """Legacy prediction payload for a single fixture."""

    fixture_id: str
    home_team_name: str
    away_team_name: str
    probabilities: PredictionProbabilities
    expected_home_goals: Optional[float] = None
    expected_away_goals: Optional[float] = None
    model_version: str = MODEL_VERSION


class WeatherResponse(BaseModel):
    """Weather forecast at kickoff."""

    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    precipitation_mm: Optional[float] = None
    weather_code: Optional[str] = None
    is_indoor: bool = False
    fetched_at_utc: Optional[datetime] = None


class ExpectedGoalsResponse(BaseModel):
    """Base and adjusted expected goals."""

    strength_home: float = Field(ge=0.0, default=0.0)
    strength_away: float = Field(ge=0.0, default=0.0)
    base_home: float = Field(ge=0.0)
    base_away: float = Field(ge=0.0)
    adjusted_home: float = Field(ge=0.0)
    adjusted_away: float = Field(ge=0.0)


class KnockoutMarketsResponse(BaseModel):
    """Knockout regulation and to-advance probabilities."""

    regulation_home_win: float = Field(ge=0.0, le=1.0)
    regulation_draw: float = Field(ge=0.0, le=1.0)
    regulation_away_win: float = Field(ge=0.0, le=1.0)
    advance_home: float = Field(ge=0.0, le=1.0)
    advance_away: float = Field(ge=0.0, le=1.0)


class ModelDiagnosticsResponse(BaseModel):
    """Transparency fields for model inputs and confidence warnings."""

    home_attack: float
    away_attack: float
    home_defense: float
    away_defense: float
    n_training_matches: int
    home_wc_matches: int
    away_wc_matches: int
    host_boost_applied: float = 0.0
    warnings: list[str] = Field(default_factory=list)


class TopScoreResponse(BaseModel):
    """Exact scoreline probability."""

    score: str
    probability: float = Field(ge=0.0, le=1.0)


class MarketProbabilitiesResponse(BaseModel):
    """Full market probabilities for a fixture."""

    home_win: float = Field(ge=0.0, le=1.0)
    draw: float = Field(ge=0.0, le=1.0)
    away_win: float = Field(ge=0.0, le=1.0)
    btts_yes: float = Field(ge=0.0, le=1.0)
    btts_no: float = Field(ge=0.0, le=1.0)
    over_under: dict[str, float]
    top_scores: list[TopScoreResponse]


class PredictionResponse(BaseModel):
    """Full prediction payload with weather and adjustment transparency."""

    fixture: FixtureResponse
    expected_goals: ExpectedGoalsResponse
    probabilities: MarketProbabilitiesResponse
    weather: Optional[WeatherResponse] = None
    pitch_type: PitchTypeSchema = "unknown"
    adjustments_applied: list[str] = Field(default_factory=list)
    weather_explanations: list[str] = Field(default_factory=list)
    diagnostics: Optional[ModelDiagnosticsResponse] = None
    knockout_markets: Optional[KnockoutMarketsResponse] = None
    prob_sum: float = Field(ge=0.0, le=1.01, default=1.0)
    model_version: str = MODEL_VERSION
    generated_at: datetime
    as_of_utc: datetime


class FixturesListResponse(BaseModel):
    """Paginated fixture list with cache metadata."""

    items: list[FixtureResponse]
    refreshed_at: datetime
    source: str


class StatusResponse(BaseModel):
    """Background refresh and provider status."""

    last_fixture_refresh_utc: Optional[datetime] = None
    last_prediction_cache_clear_utc: Optional[datetime] = None
    provider_mode: ProviderModeSchema
    fixture_counts: dict[str, int]
    refresh_interval_seconds: int
    refresh_enabled: bool
    last_refresh_error: Optional[str] = None
    ledger_prediction_count: int = 0


class CalibrationBinResponse(BaseModel):
    """Home-win probability calibration bucket."""

    bin_start: float
    bin_end: float
    count: int
    mean_predicted: float
    actual_rate: float


class AccuracySummaryResponse(BaseModel):
    """Aggregate accuracy metrics from the prediction ledger."""

    n_matches: int
    accuracy_1x2: float
    brier_score: float
    log_loss: float
    mae_total_goals: float
    ou_25_hit_rate: float = 0.0
    btts_hit_rate: float = 0.0
    calibration_bins: list[CalibrationBinResponse]
    computed_at: datetime
    model_version: str


class AccuracyFixtureResponse(BaseModel):
    """Per-fixture stored prediction vs actual result."""

    fixture_id: str
    kickoff_utc: datetime
    as_of_utc: datetime
    predicted_outcome: str
    actual_outcome: str
    correct_1x2: bool
    p_home: float
    p_draw: float
    p_away: float
    actual_home_goals: int
    actual_away_goals: int
    expected_total_goals: float
    actual_total_goals: int
    brier: float
    log_loss: float
    total_goals_error: float
    predicted_over_2_5: bool = False
    actual_over_2_5: bool = False
    correct_ou_2_5: bool = False
    predicted_btts_yes: bool = False
    actual_btts_yes: bool = False
    correct_btts: bool = False


class AccuracyFixturesListResponse(BaseModel):
    """List of per-fixture accuracy evaluations."""

    items: list[AccuracyFixtureResponse]
    computed_at: datetime


class AccuracyRecomputeResponse(BaseModel):
    """Response from POST /accuracy/recompute."""

    summary: AccuracySummaryResponse
    evaluated_count: int


class ModelInfoResponse(BaseModel):
    """Active model hyperparameters for UI display."""

    model_version: str
    team_history_limit: int
    shrinkage_prior_matches: float
    dixon_coles_rho: float
    weather_delta_scale: float
    weather_min_bucket_samples: int
    intercept_prior_goals: float
    time_decay_half_life_days: float
    tournament_min_total_xg: float
    knockout_min_total_xg: float
    knockout_dixon_coles_rho: float
    tournament_scoring_prior_weight: float
    elo_blend_weight: float
    host_nation_boost: float


class TeamTournamentStatsResponse(BaseModel):
    """WC 2026 tournament stats for one national team."""

    team_id: str
    team_name: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    avg_goals_for: float
    avg_goals_against: float
    clean_sheets: int
    form: str


class TeamStatsListResponse(BaseModel):
    """All team tournament stats for the current WC 2026 data."""

    source: str
    competition: str
    fixture_count: int
    finished_count: int
    teams: list[TeamTournamentStatsResponse]
