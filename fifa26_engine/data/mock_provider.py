"""Offline mock fixture provider for development without an API key."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from fifa26_engine.data.provider import Fixture, FixtureStatus, MatchResult
from fifa26_engine.data.stadiums import enrich_fixture

WC2026 = "FIFA World Cup 2026"


def _dt(year: int, month: int, day: int, hour: int = 19) -> datetime:
    return datetime(year, month, day, hour, 0, tzinfo=timezone.utc)


def _fx(
    fixture_id: str,
    home_id: str,
    away_id: str,
    home_name: str,
    away_name: str,
    kickoff: datetime,
    status: FixtureStatus,
    stage: str,
    venue: str,
    home_goals: int | None,
    away_goals: int | None,
) -> Fixture:
    return enrich_fixture(
        Fixture(
            fixture_id=fixture_id,
            home_team_id=home_id,
            away_team_id=away_id,
            home_team_name=home_name,
            away_team_name=away_name,
            kickoff_utc=kickoff,
            status=status,
            competition=WC2026,
            stage=stage,
            venue=venue,
            home_goals=home_goals,
            away_goals=away_goals,
        ),
    )


def _build_mock_fixtures() -> list[Fixture]:
    """Build a realistic sample World Cup 2026 fixture set (group + knockout)."""
    return [
        _fx("wc26-001", "1001", "1002", "Mexico", "Canada", _dt(2026, 6, 11), "finished", "Group A - Matchday 1", "Estadio Azteca", 2, 1),
        _fx("wc26-002", "1003", "1004", "United States", "Jamaica", _dt(2026, 6, 12), "finished", "Group A - Matchday 1", "MetLife Stadium", 3, 0),
        _fx("wc26-003", "1001", "1003", "Mexico", "United States", _dt(2026, 6, 18), "live", "Group A - Matchday 2", "Estadio Akron", 1, 1),
        _fx("wc26-004", "1002", "1004", "Canada", "Jamaica", _dt(2026, 6, 19), "scheduled", "Group A - Matchday 2", "BMO Field", None, None),
        _fx("wc26-005", "2001", "2002", "Brazil", "Serbia", _dt(2026, 6, 13), "scheduled", "Group B - Matchday 1", "SoFi Stadium", None, None),
        _fx("wc26-006", "2003", "2004", "France", "Morocco", _dt(2026, 6, 14), "scheduled", "Group B - Matchday 1", "AT&T Stadium", None, None),
        _fx("wc26-007", "2001", "2003", "Brazil", "France", _dt(2026, 6, 20), "finished", "Group B - Matchday 2", "Levi's Stadium", 2, 2),
        _fx("wc26-008", "2002", "2004", "Serbia", "Morocco", _dt(2026, 6, 21), "finished", "Group B - Matchday 2", "Lumen Field", 0, 1),
        _fx("wc26-009", "3001", "3002", "England", "Japan", _dt(2026, 6, 15), "scheduled", "Group C - Matchday 1", "Mercedes-Benz Stadium", None, None),
        _fx("wc26-010", "3003", "3004", "Argentina", "South Korea", _dt(2026, 6, 16), "finished", "Group C - Matchday 1", "Hard Rock Stadium", 1, 1),
        _fx("wc26-011", "2001", "3002", "Brazil", "Japan", _dt(2026, 7, 4), "scheduled", "Round of 16", "NRG Stadium", None, None),
        _fx("wc26-012", "2003", "3001", "France", "England", _dt(2026, 7, 5), "scheduled", "Quarter-finals", "Lincoln Financial Field", None, None),
        _fx("wc26-013", "3003", "2001", "Argentina", "Brazil", _dt(2026, 7, 9), "scheduled", "Semi-finals", "MetLife Stadium", None, None),
        _fx("wc26-014", "2001", "2003", "Brazil", "France", _dt(2026, 7, 13), "scheduled", "Final", "MetLife Stadium", None, None),
    ]


def _build_mock_team_results() -> dict[str, list[MatchResult]]:
    """Historical national-team results with weather/pitch metadata for affinity."""
    base = _dt(2025, 3, 22)
    results: dict[str, list[MatchResult]] = {
        "1001": [
            MatchResult("hist-mx-01", base, "1001", "1005", 2, 0, False, "CONCACAF Qualifiers", 26.0, 45.0, 0.0, "grass"),
            MatchResult("hist-mx-02", base + timedelta(days=14), "1006", "1001", 1, 1, True, "Friendly", 24.0, 55.0, 0.0, "grass"),
            MatchResult("hist-mx-03", base + timedelta(days=45), "1001", "1007", 3, 1, False, "CONCACAF Qualifiers", 28.0, 50.0, 0.0, "grass"),
            MatchResult("hist-mx-04", base + timedelta(days=90), "1008", "1001", 0, 2, True, "Friendly", 18.0, 60.0, 2.0, "grass"),
        ],
        "1002": [
            MatchResult("hist-ca-01", base, "1002", "1009", 1, 0, False, "CONCACAF Qualifiers", 12.0, 65.0, 0.5, "grass"),
            MatchResult("hist-ca-02", base + timedelta(days=21), "1010", "1002", 2, 2, True, "Friendly", 10.0, 70.0, 1.0, "grass"),
            MatchResult("hist-ca-03", base + timedelta(days=60), "1002", "1005", 2, 1, False, "CONCACAF Qualifiers", 8.0, 72.0, 3.0, "grass"),
        ],
        "1003": [
            MatchResult("hist-us-01", base, "1003", "1011", 4, 0, False, "CONCACAF Qualifiers", 22.0, 50.0, 0.0, "grass"),
            MatchResult("hist-us-02", base + timedelta(days=30), "1012", "1003", 1, 2, True, "Friendly", 16.0, 58.0, 0.0, "hybrid"),
            MatchResult("hist-us-03", base + timedelta(days=75), "1003", "1006", 2, 0, False, "CONCACAF Qualifiers", 30.0, 48.0, 0.0, "grass"),
            MatchResult("hist-us-04", base + timedelta(days=120), "1003", "1001", 1, 1, True, "Friendly", 20.0, 55.0, 0.0, "grass"),
        ],
        "1004": [
            MatchResult("hist-jm-01", base, "1004", "1013", 3, 0, False, "CONCACAF Qualifiers", 29.0, 75.0, 0.0, "grass"),
            MatchResult("hist-jm-02", base + timedelta(days=40), "1014", "1004", 0, 1, True, "Friendly", 27.0, 80.0, 1.5, "grass"),
        ],
        "2001": [
            MatchResult("hist-br-01", base, "2001", "2010", 1, 0, False, "CONMEBOL Qualifiers", 30.0, 70.0, 0.0, "grass"),
            MatchResult("hist-br-02", base + timedelta(days=25), "2011", "2001", 0, 2, True, "Friendly", 32.0, 68.0, 0.0, "grass"),
            MatchResult("hist-br-03", base + timedelta(days=70), "2001", "2012", 2, 0, False, "CONMEBOL Qualifiers", 28.0, 65.0, 0.0, "grass"),
            MatchResult("hist-br-04", _dt(2022, 12, 9), "2001", "2013", 4, 1, True, "FIFA World Cup 2022", 26.0, 60.0, 0.0, "grass"),
            MatchResult("hist-br-05", base + timedelta(days=100), "2001", "2003", 0, 1, True, "Friendly", 31.0, 62.0, 0.0, "grass"),
            MatchResult("hist-br-06", base + timedelta(days=130), "2001", "2015", 3, 0, False, "Friendly", 33.0, 72.0, 0.0, "grass"),
        ],
        "2003": [
            MatchResult("hist-fr-01", base, "2003", "2014", 3, 0, False, "UEFA Qualifiers", 14.0, 60.0, 1.0, "grass"),
            MatchResult("hist-fr-02", base + timedelta(days=35), "2015", "2003", 1, 2, True, "Friendly", 18.0, 55.0, 0.0, "grass"),
            MatchResult("hist-fr-03", _dt(2022, 12, 18), "2003", "3003", 3, 3, True, "FIFA World Cup 2022", 18.0, 50.0, 0.0, "grass"),
            MatchResult("hist-fr-04", base + timedelta(days=85), "2003", "2016", 2, 0, False, "UEFA Qualifiers", 10.0, 68.0, 2.5, "grass"),
        ],
        "3001": [
            MatchResult("hist-en-01", base, "3001", "3010", 2, 0, False, "UEFA Qualifiers", 8.0, 75.0, 2.0, "grass"),
            MatchResult("hist-en-02", base + timedelta(days=28), "3011", "3001", 0, 0, True, "Friendly", 6.0, 80.0, 4.0, "grass"),
            MatchResult("hist-en-03", _dt(2024, 7, 14), "3001", "2014", 2, 1, True, "UEFA Euro 2024", 20.0, 55.0, 0.0, "grass"),
            MatchResult("hist-en-04", base + timedelta(days=95), "3001", "3012", 1, 0, False, "UEFA Qualifiers", 5.0, 82.0, 3.0, "grass"),
        ],
        "3003": [
            MatchResult("hist-ar-01", base, "3003", "2010", 1, 0, False, "CONMEBOL Qualifiers", 22.0, 58.0, 0.0, "grass"),
            MatchResult("hist-ar-02", base + timedelta(days=32), "2011", "3003", 0, 3, True, "Friendly", 24.0, 60.0, 0.0, "grass"),
            MatchResult("hist-ar-03", _dt(2022, 12, 18), "3003", "2003", 3, 3, True, "FIFA World Cup 2022", 18.0, 50.0, 0.0, "grass"),
            MatchResult("hist-ar-04", base + timedelta(days=88), "3003", "2012", 2, 0, False, "CONMEBOL Qualifiers", 19.0, 62.0, 0.0, "grass"),
        ],
        "3002": [
            MatchResult("hist-jp-01", base, "3002", "3013", 4, 1, False, "AFC Qualifiers", 18.0, 65.0, 0.0, "grass"),
            MatchResult("hist-jp-02", base + timedelta(days=50), "3014", "3002", 0, 2, True, "Friendly", 28.0, 70.0, 0.0, "grass"),
            MatchResult("hist-jp-03", base + timedelta(days=110), "3002", "3015", 1, 0, False, "AFC Qualifiers", 8.0, 78.0, 5.0, "grass"),
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
