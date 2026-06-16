"""Pydantic schemas for API request and response models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MatchResultSchema(BaseModel):
    """Score and status for a completed or live fixture."""

    home_goals: int = Field(ge=0)
    away_goals: int = Field(ge=0)
    status: str = "FT"


class FixtureResponse(BaseModel):
    """Serialized fixture returned by the API."""

    fixture_id: int
    competition_id: int
    season: int
    round: str
    kickoff_utc: datetime
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str
    venue: Optional[str] = None
    result: Optional[MatchResultSchema] = None


class PredictionProbabilities(BaseModel):
    """Match outcome probabilities."""

    home_win: float = Field(ge=0.0, le=1.0)
    draw: float = Field(ge=0.0, le=1.0)
    away_win: float = Field(ge=0.0, le=1.0)


class MatchPredictionResponse(BaseModel):
    """Prediction payload for a single fixture."""

    fixture_id: int
    home_team_name: str
    away_team_name: str
    probabilities: PredictionProbabilities
    expected_home_goals: Optional[float] = None
    expected_away_goals: Optional[float] = None
    model_version: str = "0.1.0-scaffold"
