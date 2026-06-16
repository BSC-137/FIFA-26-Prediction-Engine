"""Offline mock fixture provider for development without an API key."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fifa26_engine.data.provider import FixtureRecord, MatchResult


def _build_mock_fixtures() -> list[FixtureRecord]:
    """Build a realistic sample World Cup 2026 group-stage fixture set."""
    kickoff_base = datetime(2026, 6, 11, 19, 0, tzinfo=timezone.utc)
    return [
        FixtureRecord(
            fixture_id=2026001,
            competition_id=1,
            season=2026,
            round="Group A - 1",
            kickoff_utc=kickoff_base,
            home_team_id=1001,
            home_team_name="Mexico",
            away_team_id=1002,
            away_team_name="Canada",
            venue="Estadio Azteca",
            result=MatchResult(home_goals=2, away_goals=1),
        ),
        FixtureRecord(
            fixture_id=2026002,
            competition_id=1,
            season=2026,
            round="Group A - 1",
            kickoff_utc=kickoff_base.replace(day=12),
            home_team_id=1003,
            home_team_name="United States",
            away_team_id=1004,
            away_team_name="Jamaica",
            venue="MetLife Stadium",
            result=MatchResult(home_goals=3, away_goals=0),
        ),
        FixtureRecord(
            fixture_id=2026003,
            competition_id=1,
            season=2026,
            round="Group B - 1",
            kickoff_utc=kickoff_base.replace(day=13),
            home_team_id=2001,
            home_team_name="Brazil",
            away_team_id=2002,
            away_team_name="Serbia",
            venue="SoFi Stadium",
            result=None,
        ),
        FixtureRecord(
            fixture_id=2026004,
            competition_id=1,
            season=2026,
            round="Group B - 1",
            kickoff_utc=kickoff_base.replace(day=14),
            home_team_id=2003,
            home_team_name="France",
            away_team_id=2004,
            away_team_name="Morocco",
            venue="AT&T Stadium",
            result=None,
        ),
        FixtureRecord(
            fixture_id=2026005,
            competition_id=1,
            season=2026,
            round="Group C - 1",
            kickoff_utc=kickoff_base.replace(day=15),
            home_team_id=3001,
            home_team_name="England",
            away_team_id=3002,
            away_team_name="Japan",
            venue="Mercedes-Benz Stadium",
            result=None,
        ),
        FixtureRecord(
            fixture_id=2026006,
            competition_id=1,
            season=2026,
            round="Group C - 1",
            kickoff_utc=kickoff_base.replace(day=16),
            home_team_id=3003,
            home_team_name="Argentina",
            away_team_id=3004,
            away_team_name="South Korea",
            venue="Hard Rock Stadium",
            result=MatchResult(home_goals=1, away_goals=1),
        ),
    ]


class MockFixtureProvider:
    """Concrete ``FixtureProvider`` serving static offline World Cup fixtures."""

    def __init__(self, fixtures: Optional[list[FixtureRecord]] = None) -> None:
        """Initialize with optional custom fixture list."""
        self._fixtures = fixtures if fixtures is not None else _build_mock_fixtures()
        self._by_id = {fixture.fixture_id: fixture for fixture in self._fixtures}

    async def get_fixtures(
        self,
        competition_id: int,
        season: int,
    ) -> list[FixtureRecord]:
        """Return mock fixtures filtered by competition and season."""
        return [
            fixture
            for fixture in self._fixtures
            if fixture.competition_id == competition_id and fixture.season == season
        ]

    async def get_fixture(self, fixture_id: int) -> Optional[FixtureRecord]:
        """Return a mock fixture by ID."""
        return self._by_id.get(fixture_id)

    async def get_team_fixtures(
        self,
        team_id: int,
        season: int,
    ) -> list[FixtureRecord]:
        """Return mock fixtures involving the given team."""
        return [
            fixture
            for fixture in self._fixtures
            if fixture.season == season
            and (fixture.home_team_id == team_id or fixture.away_team_id == team_id)
        ]
