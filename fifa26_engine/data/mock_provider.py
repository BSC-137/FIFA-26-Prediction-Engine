"""Offline mock fixture provider for development without an API key."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from fifa26_engine.data.provider import Fixture, FixtureStatus, MatchResult

WC2026 = "FIFA World Cup 2026"


def _dt(year: int, month: int, day: int, hour: int = 19) -> datetime:
    return datetime(year, month, day, hour, 0, tzinfo=timezone.utc)


def _build_mock_fixtures() -> list[Fixture]:
    """Build a realistic sample World Cup 2026 fixture set (group + knockout)."""
    return [
        # Group A
        Fixture(
            fixture_id="wc26-001",
            home_team_id="1001",
            away_team_id="1002",
            home_team_name="Mexico",
            away_team_name="Canada",
            kickoff_utc=_dt(2026, 6, 11),
            status="finished",
            competition=WC2026,
            stage="Group A - Matchday 1",
            venue="Estadio Azteca",
            home_goals=2,
            away_goals=1,
        ),
        Fixture(
            fixture_id="wc26-002",
            home_team_id="1003",
            away_team_id="1004",
            home_team_name="United States",
            away_team_name="Jamaica",
            kickoff_utc=_dt(2026, 6, 12),
            status="finished",
            competition=WC2026,
            stage="Group A - Matchday 1",
            venue="MetLife Stadium",
            home_goals=3,
            away_goals=0,
        ),
        Fixture(
            fixture_id="wc26-003",
            home_team_id="1001",
            away_team_id="1003",
            home_team_name="Mexico",
            away_team_name="United States",
            kickoff_utc=_dt(2026, 6, 18),
            status="live",
            competition=WC2026,
            stage="Group A - Matchday 2",
            venue="Estadio Akron",
            home_goals=1,
            away_goals=1,
        ),
        Fixture(
            fixture_id="wc26-004",
            home_team_id="1002",
            away_team_id="1004",
            home_team_name="Canada",
            away_team_name="Jamaica",
            kickoff_utc=_dt(2026, 6, 19),
            status="scheduled",
            competition=WC2026,
            stage="Group A - Matchday 2",
            venue="BMO Field",
            home_goals=None,
            away_goals=None,
        ),
        # Group B
        Fixture(
            fixture_id="wc26-005",
            home_team_id="2001",
            away_team_id="2002",
            home_team_name="Brazil",
            away_team_name="Serbia",
            kickoff_utc=_dt(2026, 6, 13),
            status="scheduled",
            competition=WC2026,
            stage="Group B - Matchday 1",
            venue="SoFi Stadium",
            home_goals=None,
            away_goals=None,
        ),
        Fixture(
            fixture_id="wc26-006",
            home_team_id="2003",
            away_team_id="2004",
            home_team_name="France",
            away_team_name="Morocco",
            kickoff_utc=_dt(2026, 6, 14),
            status="scheduled",
            competition=WC2026,
            stage="Group B - Matchday 1",
            venue="AT&T Stadium",
            home_goals=None,
            away_goals=None,
        ),
        Fixture(
            fixture_id="wc26-007",
            home_team_id="2001",
            away_team_id="2003",
            home_team_name="Brazil",
            away_team_name="France",
            kickoff_utc=_dt(2026, 6, 20),
            status="finished",
            competition=WC2026,
            stage="Group B - Matchday 2",
            venue="Levi's Stadium",
            home_goals=2,
            away_goals=2,
        ),
        Fixture(
            fixture_id="wc26-008",
            home_team_id="2002",
            away_team_id="2004",
            home_team_name="Serbia",
            away_team_name="Morocco",
            kickoff_utc=_dt(2026, 6, 21),
            status="finished",
            competition=WC2026,
            stage="Group B - Matchday 2",
            venue="Lumen Field",
            home_goals=0,
            away_goals=1,
        ),
        # Group C
        Fixture(
            fixture_id="wc26-009",
            home_team_id="3001",
            away_team_id="3002",
            home_team_name="England",
            away_team_name="Japan",
            kickoff_utc=_dt(2026, 6, 15),
            status="scheduled",
            competition=WC2026,
            stage="Group C - Matchday 1",
            venue="Mercedes-Benz Stadium",
            home_goals=None,
            away_goals=None,
        ),
        Fixture(
            fixture_id="wc26-010",
            home_team_id="3003",
            away_team_id="3004",
            home_team_name="Argentina",
            away_team_name="South Korea",
            kickoff_utc=_dt(2026, 6, 16),
            status="finished",
            competition=WC2026,
            stage="Group C - Matchday 1",
            venue="Hard Rock Stadium",
            home_goals=1,
            away_goals=1,
        ),
        # Knockout
        Fixture(
            fixture_id="wc26-011",
            home_team_id="2001",
            away_team_id="3002",
            home_team_name="Brazil",
            away_team_name="Japan",
            kickoff_utc=_dt(2026, 7, 4),
            status="scheduled",
            competition=WC2026,
            stage="Round of 16",
            venue="NRG Stadium",
            home_goals=None,
            away_goals=None,
        ),
        Fixture(
            fixture_id="wc26-012",
            home_team_id="2003",
            away_team_id="3001",
            home_team_name="France",
            away_team_name="England",
            kickoff_utc=_dt(2026, 7, 5),
            status="scheduled",
            competition=WC2026,
            stage="Quarter-finals",
            venue="Lincoln Financial Field",
            home_goals=None,
            away_goals=None,
        ),
        Fixture(
            fixture_id="wc26-013",
            home_team_id="3003",
            away_team_id="2001",
            home_team_name="Argentina",
            away_team_name="Brazil",
            kickoff_utc=_dt(2026, 7, 9),
            status="scheduled",
            competition=WC2026,
            stage="Semi-finals",
            venue="MetLife Stadium",
            home_goals=None,
            away_goals=None,
        ),
        Fixture(
            fixture_id="wc26-014",
            home_team_id="2001",
            away_team_id="2003",
            home_team_name="Brazil",
            away_team_name="France",
            kickoff_utc=_dt(2026, 7, 13),
            status="scheduled",
            competition=WC2026,
            stage="Final",
            venue="MetLife Stadium",
            home_goals=None,
            away_goals=None,
        ),
    ]


def _build_mock_team_results() -> dict[str, list[MatchResult]]:
    """Historical national-team results for modeling (qualifiers, friendlies, prior WC)."""
    base = _dt(2025, 3, 22)
    results: dict[str, list[MatchResult]] = {
        "1001": [
            MatchResult("hist-mx-01", base, "1001", "1005", 2, 0, False, "CONCACAF Qualifiers"),
            MatchResult("hist-mx-02", base + timedelta(days=14), "1006", "1001", 1, 1, True, "Friendly"),
            MatchResult("hist-mx-03", base + timedelta(days=45), "1001", "1007", 3, 1, False, "CONCACAF Qualifiers"),
            MatchResult("hist-mx-04", base + timedelta(days=90), "1008", "1001", 0, 2, True, "Friendly"),
        ],
        "1002": [
            MatchResult("hist-ca-01", base, "1002", "1009", 1, 0, False, "CONCACAF Qualifiers"),
            MatchResult("hist-ca-02", base + timedelta(days=21), "1010", "1002", 2, 2, True, "Friendly"),
            MatchResult("hist-ca-03", base + timedelta(days=60), "1002", "1005", 2, 1, False, "CONCACAF Qualifiers"),
        ],
        "1003": [
            MatchResult("hist-us-01", base, "1003", "1011", 4, 0, False, "CONCACAF Qualifiers"),
            MatchResult("hist-us-02", base + timedelta(days=30), "1012", "1003", 1, 2, True, "Friendly"),
            MatchResult("hist-us-03", base + timedelta(days=75), "1003", "1006", 2, 0, False, "CONCACAF Qualifiers"),
            MatchResult("hist-us-04", base + timedelta(days=120), "1003", "1001", 1, 1, True, "Friendly"),
        ],
        "1004": [
            MatchResult("hist-jm-01", base, "1004", "1013", 3, 0, False, "CONCACAF Qualifiers"),
            MatchResult("hist-jm-02", base + timedelta(days=40), "1014", "1004", 0, 1, True, "Friendly"),
        ],
        "2001": [
            MatchResult("hist-br-01", base, "2001", "2010", 1, 0, False, "CONMEBOL Qualifiers"),
            MatchResult("hist-br-02", base + timedelta(days=25), "2011", "2001", 0, 2, True, "Friendly"),
            MatchResult("hist-br-03", base + timedelta(days=70), "2001", "2012", 2, 0, False, "CONMEBOL Qualifiers"),
            MatchResult("hist-br-04", _dt(2022, 12, 9), "2001", "2013", 4, 1, True, "FIFA World Cup 2022"),
            MatchResult("hist-br-05", base + timedelta(days=100), "2001", "2003", 0, 1, True, "Friendly"),
        ],
        "2003": [
            MatchResult("hist-fr-01", base, "2003", "2014", 3, 0, False, "UEFA Qualifiers"),
            MatchResult("hist-fr-02", base + timedelta(days=35), "2015", "2003", 1, 2, True, "Friendly"),
            MatchResult("hist-fr-03", _dt(2022, 12, 18), "2003", "3003", 3, 3, True, "FIFA World Cup 2022"),
            MatchResult("hist-fr-04", base + timedelta(days=85), "2003", "2016", 2, 0, False, "UEFA Qualifiers"),
        ],
        "3001": [
            MatchResult("hist-en-01", base, "3001", "3010", 2, 0, False, "UEFA Qualifiers"),
            MatchResult("hist-en-02", base + timedelta(days=28), "3011", "3001", 0, 0, True, "Friendly"),
            MatchResult("hist-en-03", _dt(2024, 7, 14), "3001", "2014", 2, 1, True, "UEFA Euro 2024"),
            MatchResult("hist-en-04", base + timedelta(days=95), "3001", "3012", 1, 0, False, "UEFA Qualifiers"),
        ],
        "3003": [
            MatchResult("hist-ar-01", base, "3003", "2010", 1, 0, False, "CONMEBOL Qualifiers"),
            MatchResult("hist-ar-02", base + timedelta(days=32), "2011", "3003", 0, 3, True, "Friendly"),
            MatchResult("hist-ar-03", _dt(2022, 12, 18), "3003", "2003", 3, 3, True, "FIFA World Cup 2022"),
            MatchResult("hist-ar-04", base + timedelta(days=88), "3003", "2012", 2, 0, False, "CONMEBOL Qualifiers"),
        ],
        "3002": [
            MatchResult("hist-jp-01", base, "3002", "3013", 4, 1, False, "AFC Qualifiers"),
            MatchResult("hist-jp-02", base + timedelta(days=50), "3014", "3002", 0, 2, True, "Friendly"),
            MatchResult("hist-jp-03", base + timedelta(days=110), "3002", "3015", 1, 0, False, "AFC Qualifiers"),
        ],
    }
    return results


def _apply_limit(items: Iterable[Fixture], limit: int) -> list[Fixture]:
    if limit <= 0:
        return []
    return list(items)[:limit]


class MockFixtureProvider:
    """Concrete ``FixtureProvider`` serving static offline World Cup data."""

    def __init__(
        self,
        fixtures: list[Fixture] | None = None,
        team_results: dict[str, list[MatchResult]] | None = None,
    ) -> None:
        """Initialize with optional custom fixture and history data."""
        self._fixtures = fixtures if fixtures is not None else _build_mock_fixtures()
        self._team_results = team_results if team_results is not None else _build_mock_team_results()
        self._by_id = {fixture.fixture_id: fixture for fixture in self._fixtures}

    async def get_fixtures(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[Fixture]:
        """Return mock World Cup fixtures, optionally filtered by status."""
        fixtures = self._fixtures
        if status is not None:
            normalized = status.lower()
            fixtures = [fixture for fixture in fixtures if fixture.status == normalized]
        return _apply_limit(fixtures, limit)

    async def get_team_results(
        self,
        team_id: str,
        limit: int = 30,
    ) -> list[MatchResult]:
        """Return mock historical results for a team, most recent first."""
        history = self._team_results.get(team_id, [])
        sorted_history = sorted(history, key=lambda match: match.date, reverse=True)
        return _apply_limit(sorted_history, limit)

    async def get_fixture_by_id(self, fixture_id: str) -> Fixture | None:
        """Return a mock fixture by ID."""
        return self._by_id.get(fixture_id)
