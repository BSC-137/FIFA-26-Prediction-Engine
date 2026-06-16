"""Pydantic schemas for API request and response models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

FixtureStatusSchema = Literal["scheduled", "live", "finished"]


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
    """Match outcome probabilities."""

    home_win: float = Field(ge=0.0, le=1.0)
    draw: float = Field(ge=0.0, le=1.0)
    away_win: float = Field(ge=0.0, le=1.0)


class MatchPredictionResponse(BaseModel):
    """Prediction payload for a single fixture."""

    fixture_id: str
    home_team_name: str
    away_team_name: str
    probabilities: PredictionProbabilities
    expected_home_goals: Optional[float] = None
    expected_away_goals: Optional[float] = None
    model_version: str = "0.1.0-scaffold"
