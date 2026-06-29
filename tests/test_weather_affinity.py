"""Tests for weather/pitch affinity engine."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from fifa26_engine.data.provider import MatchResult, WeatherConditions
from fifa26_engine.models.weather_affinity import WeatherAffinityEngine

UTC = timezone.utc
BASE = datetime(2025, 1, 1, tzinfo=UTC)


def _match(
    match_id: str,
    team: str,
    opp: str,
    scored: int,
    conceded: int,
    temp: float,
    precip: float = 0.0,
    pitch: str = "grass",
) -> MatchResult:
    return MatchResult(
        match_id=match_id,
        date=BASE,
        home_team_id=team,
        away_team_id=opp,
        home_goals=scored,
        away_goals=conceded,
        is_neutral=False,
        competition="Friendly",
        temperature_c=temp,
        precipitation_mm=precip,
        pitch_type=pitch,  # type: ignore[arg-type]
    )


def test_fit_and_compute_modifiers_hot_team() -> None:
    results = [
        _match(f"hot-{i}", "HOT", "X", 3, 0, temp=30.0) for i in range(6)
    ] + [
        _match(f"mild-{i}", "HOT", "X", 1, 1, temp=18.0) for i in range(6)
    ]
    engine = WeatherAffinityEngine.from_results(results)
    weather = WeatherConditions(
        temperature_c=30.0,
        humidity_pct=70.0,
        wind_speed_kmh=10.0,
        precipitation_mm=0.0,
        weather_code="heat",
        fetched_at_utc=BASE,
    )
    home_mult, away_mult, labels = engine.compute_modifiers("HOT", "OTHER", weather, "grass")
    assert 0.94 <= home_mult <= 1.06
    assert away_mult == 1.0
    assert labels


def test_unknown_weather_returns_neutral_modifiers() -> None:
    engine = WeatherAffinityEngine()
    engine.fit([])
    home_mult, away_mult, labels = engine.compute_modifiers("A", "B", None, "grass")
    assert home_mult == 1.0
    assert away_mult == 1.0
    assert labels == []


def test_unknown_team_gets_neutral_modifier() -> None:
    results = [_match("m1", "HOT", "X", 2, 0, temp=30.0) for _ in range(6)]
    engine = WeatherAffinityEngine.from_results(results)
    weather = WeatherConditions(
        temperature_c=30.0,
        humidity_pct=70.0,
        wind_speed_kmh=10.0,
        precipitation_mm=0.0,
        weather_code="heat",
        fetched_at_utc=BASE,
    )
    home_mult, _, _ = engine.compute_modifiers("UNKNOWN", "HOT", weather, "grass")
    assert home_mult == 1.0
