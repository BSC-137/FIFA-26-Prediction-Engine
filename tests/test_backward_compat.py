"""Backward compatibility tests for optional domain model fields."""

from __future__ import annotations

from datetime import datetime, timezone

from fifa26_engine.data.provider import Fixture, MatchResult

UTC = timezone.utc


def test_fixture_without_optional_fields() -> None:
    fixture = Fixture(
        fixture_id="legacy-1",
        home_team_id="1",
        away_team_id="2",
        home_team_name="Home",
        away_team_name="Away",
        kickoff_utc=datetime(2026, 6, 1, tzinfo=UTC),
        status="scheduled",
        competition="Friendly",
        stage="Group",
        venue=None,
        home_goals=None,
        away_goals=None,
    )
    assert fixture.pitch_type == "unknown"
    assert fixture.stadium_lat is None


def test_match_result_without_weather_fields() -> None:
    result = MatchResult(
        match_id="legacy-r1",
        date=datetime(2025, 1, 1, tzinfo=UTC),
        home_team_id="1",
        away_team_id="2",
        home_goals=1,
        away_goals=1,
        is_neutral=True,
        competition="Friendly",
    )
    assert result.temperature_c is None
    assert result.pitch_type is None
