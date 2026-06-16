"""Abstract fixture data provider protocol and shared domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, runtime_checkable

FixtureStatus = Literal["scheduled", "live", "finished"]


@dataclass(frozen=True)
class Team:
    """National team identity."""

    team_id: str
    name: str
    code: str | None = None


@dataclass(frozen=True)
class Fixture:
    """World Cup fixture normalized across providers."""

    fixture_id: str
    home_team_id: str
    away_team_id: str
    home_team_name: str
    away_team_name: str
    kickoff_utc: datetime
    status: FixtureStatus
    competition: str
    stage: str
    venue: str | None
    home_goals: int | None
    away_goals: int | None


@dataclass(frozen=True)
class MatchResult:
    """Historical national-team match result for modeling."""

    match_id: str
    date: datetime
    home_team_id: str
    away_team_id: str
    home_goals: int
    away_goals: int
    is_neutral: bool
    competition: str


@runtime_checkable
class FixtureProvider(Protocol):
    """Protocol for fetching World Cup fixtures and national-team match history."""

    async def get_fixtures(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[Fixture]:
        """Return World Cup fixtures, optionally filtered by status."""
        ...

    async def get_team_results(
        self,
        team_id: str,
        limit: int = 30,
    ) -> list[MatchResult]:
        """Return recent finished matches for a national team."""
        ...

    async def get_fixture_by_id(self, fixture_id: str) -> Fixture | None:
        """Return a single fixture by ID, or ``None`` if not found."""
        ...
