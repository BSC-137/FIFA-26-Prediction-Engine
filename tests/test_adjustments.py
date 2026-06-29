"""Tests for structured match context adjustments."""

from __future__ import annotations

from datetime import datetime, timezone

from fifa26_engine.data.provider import WeatherConditions
from fifa26_engine.models.adjustments import AdjustmentEngine, MatchContext

UTC = timezone.utc


def test_knockout_reduces_xg() -> None:
    engine = AdjustmentEngine()
    context = MatchContext(is_knockout=True)
    home, away, labels = engine.apply(1.5, 1.2, context)
    assert home < 1.5
    assert away < 1.2
    assert "knockout_caution" in labels


def test_missing_players_penalty() -> None:
    engine = AdjustmentEngine()
    context = MatchContext(home_missing_key_players=2)
    home, away, labels = engine.apply(1.5, 1.2, context)
    assert home < 1.5
    assert away == 1.2
    assert any("home_missing_players" in label for label in labels)


def test_weather_modifiers_applied() -> None:
    engine = AdjustmentEngine()
    context = MatchContext()
    home, away, labels = engine.apply(
        1.5,
        1.2,
        context,
        weather_modifiers=(1.04, 0.97, ["home_affinity:hot_dry_grass"]),
    )
    assert home > 1.5
    assert away < 1.2
    assert "home_affinity:hot_dry_grass" in labels


def test_total_adjustment_capped() -> None:
    engine = AdjustmentEngine()
    context = MatchContext(
        home_missing_key_players=3,
        away_missing_key_players=3,
        is_knockout=True,
    )
    base_home, base_away = 1.5, 1.5
    home, away, _ = engine.apply(base_home, base_away, context)
    base_total = base_home + base_away
    adjusted_total = home + away
    assert adjusted_total <= base_total * 1.08 + 1e-9
    assert adjusted_total >= base_total * 0.92 - 1e-9


def test_short_rest_penalty() -> None:
    engine = AdjustmentEngine()
    context = MatchContext(home_days_rest=3)
    home, away, labels = engine.apply(1.4, 1.4, context)
    assert home < 1.4
    assert any("home_short_rest" in label for label in labels)
