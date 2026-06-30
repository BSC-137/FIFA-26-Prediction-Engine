"""Tests for walk-forward backtesting leakage guards and determinism."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from fifa26_engine.data.mock_provider import MockFixtureProvider, _dt, _fx
from fifa26_engine.data.provider import Fixture, MatchResult
from fifa26_engine.data.weather_provider import MockWeatherProvider
from fifa26_engine.scripts.backtest_walkforward import (
    build_training_results,
    run_walkforward_backtest,
)

UTC = timezone.utc


def _tiny_fixtures() -> list[Fixture]:
    """Six finished fixtures on consecutive days for walk-forward tests."""
    base = _dt(2026, 6, 1, 15)
    specs = [
        ("wf-01", "t01", "t02", 2, 0),
        ("wf-02", "t02", "t03", 1, 1),
        ("wf-03", "t03", "t04", 0, 2),
        ("wf-04", "t04", "t05", 3, 1),
        ("wf-05", "t05", "t06", 1, 0),
        ("wf-06", "t06", "t01", 2, 2),
    ]
    fixtures: list[Fixture] = []
    for index, (fixture_id, home_id, away_id, home_goals, away_goals) in enumerate(specs):
        fixtures.append(
            _fx(
                fixture_id,
                home_id,
                away_id,
                f"Team {home_id}",
                f"Team {away_id}",
                base + timedelta(days=index),
                "finished",
                "Group A - Matchday 1",
                "Test Stadium",
                home_goals,
                away_goals,
            ),
        )
    return fixtures


def _tiny_team_results() -> dict[str, list[MatchResult]]:
    """Minimal pre-tournament history for strength fitting."""
    base = datetime(2025, 1, 1, 12, tzinfo=UTC)
    return {
        "t01": [
            MatchResult("hist-t01", base, "t01", "t99", 2, 0, False, "Friendly", 20.0, 50.0, 0.0, "grass"),
        ],
        "t02": [
            MatchResult("hist-t02", base, "t02", "t98", 1, 1, False, "Friendly", 18.0, 55.0, 0.0, "grass"),
        ],
        "t03": [
            MatchResult("hist-t03", base, "t03", "t97", 0, 1, False, "Friendly", 22.0, 48.0, 0.0, "grass"),
        ],
        "t04": [
            MatchResult("hist-t04", base, "t04", "t96", 3, 0, False, "Friendly", 25.0, 45.0, 0.0, "grass"),
        ],
        "t05": [
            MatchResult("hist-t05", base, "t05", "t95", 1, 2, False, "Friendly", 16.0, 60.0, 1.0, "grass"),
        ],
        "t06": [
            MatchResult("hist-t06", base, "t06", "t94", 2, 2, False, "Friendly", 19.0, 52.0, 0.0, "grass"),
        ],
    }


def _tiny_provider() -> MockFixtureProvider:
    return MockFixtureProvider(fixtures=_tiny_fixtures(), team_results=_tiny_team_results())


def test_training_excludes_target_fixture() -> None:
    fixtures = _tiny_fixtures()
    base_results = list(_tiny_team_results()["t01"]) + list(_tiny_team_results()["t02"])
    target = fixtures[2]
    training = build_training_results(base_results, fixtures, target.kickoff_utc)
    training_ids = {result.match_id for result in training}
    assert target.fixture_id not in training_ids


def test_training_excludes_future_fixtures() -> None:
    fixtures = _tiny_fixtures()
    base_results: list[MatchResult] = []
    for history in _tiny_team_results().values():
        base_results.extend(history)

    target = fixtures[2]
    training = build_training_results(base_results, fixtures, target.kickoff_utc)
    cutoff = target.kickoff_utc
    for result in training:
        assert result.date < cutoff
    future_fixture_ids = {fixture.fixture_id for fixture in fixtures[3:]}
    training_ids = {result.match_id for result in training}
    assert future_fixture_ids.isdisjoint(training_ids)


@pytest.mark.asyncio
async def test_walkforward_metrics_are_deterministic() -> None:
    provider = _tiny_provider()
    weather = MockWeatherProvider()

    report_a = await run_walkforward_backtest(provider, weather_provider=weather)
    report_b = await run_walkforward_backtest(provider, weather_provider=weather)

    assert report_a.overall.n_matches == 6
    assert report_b.overall.n_matches == 6
    assert report_a.overall.accuracy_1x2 == report_b.overall.accuracy_1x2
    assert report_a.overall.brier_score == report_b.overall.brier_score
    assert report_a.overall.log_loss == report_b.overall.log_loss
    assert report_a.overall.ou_25_hit_rate == report_b.overall.ou_25_hit_rate
    assert report_a.overall.btts_hit_rate == report_b.overall.btts_hit_rate
    assert report_a.overall.mae_total_goals == report_b.overall.mae_total_goals
