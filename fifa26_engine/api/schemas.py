"""Pydantic schemas for API request and response models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

FixtureStatusSchema = Literal["scheduled", "live", "finished"]
PitchTypeSchema = Literal["grass", "hybrid", "artificial", "unknown"]
MODEL_VERSION = "0.2.0"


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

    base_home: float = Field(ge=0.0)
    base_away: float = Field(ge=0.0)
    adjusted_home: float = Field(ge=0.0)
    adjusted_away: float = Field(ge=0.0)


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
    model_version: str = MODEL_VERSION
    generated_at: datetime
    as_of_utc: datetime


class FixturesListResponse(BaseModel):
    """Paginated fixture list with cache metadata."""

    items: list[FixtureResponse]
    refreshed_at: datetime
    source: str
