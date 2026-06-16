"""Abstract fixture data provider protocol and shared types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class MatchResult:
    """Final or in-progress score for a fixture."""

    home_goals: int
    away_goals: int
    status: str = "FT"


@dataclass(frozen=True)
class FixtureRecord:
    """Normalized fixture representation used across providers."""

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
    result: Optional[MatchResult] = None


@runtime_checkable
class FixtureProvider(Protocol):
    """Protocol for fetching World Cup fixtures and results."""

    async def get_fixtures(
        self,
        competition_id: int,
        season: int,
    ) -> list[FixtureRecord]:
        """Return all fixtures for a competition and season."""
        ...

    async def get_fixture(self, fixture_id: int) -> Optional[FixtureRecord]:
        """Return a single fixture by ID, or ``None`` if not found."""
        ...

    async def get_team_fixtures(
        self,
        team_id: int,
        season: int,
    ) -> list[FixtureRecord]:
        """Return fixtures involving a specific team for a season."""
        ...
