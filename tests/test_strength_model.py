"""Tests for Poisson team strength / xG model."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from fifa26_engine.data.provider import Fixture, MatchResult
from fifa26_engine.models.strength import TeamStrengthModel, clamp_xg

UTC = timezone.utc
BASE_DATE = datetime(2025, 1, 1, tzinfo=UTC)


def _result(
    match_id: str,
    day_offset: int,
    home_id: str,
    away_id: str,
    home_goals: int,
    away_goals: int,
    *,
    is_neutral: bool = False,
    competition: str = "Friendly",
) -> MatchResult:
    return MatchResult(
        match_id=match_id,
        date=BASE_DATE + timedelta(days=day_offset),
        home_team_id=home_id,
        away_team_id=away_id,
        home_goals=home_goals,
        away_goals=away_goals,
        is_neutral=is_neutral,
        competition=competition,
    )


def _build_synthetic_results() -> list[MatchResult]:
    """Strong team ``STR`` scores heavily; weak team ``WEAK`` concedes heavily."""
    results: list[MatchResult] = []
    opponents = ["OPP1", "OPP2", "OPP3", "OPP4", "OPP5"]
    day = 0
    for opponent in opponents:
        results.append(_result(f"str-h-{opponent}", day, "STR", opponent, 3, 0))
        day += 1
        results.append(_result(f"str-a-{opponent}", day, opponent, "STR", 0, 2))
        day += 1
        results.append(_result(f"weak-h-{opponent}", day, "WEAK", opponent, 0, 2))
        day += 1
        results.append(_result(f"weak-a-{opponent}", day, opponent, "WEAK", 3, 0))
        day += 1
    return results


@pytest.fixture
def fitted_model() -> TeamStrengthModel:
    return TeamStrengthModel.from_results(_build_synthetic_results())


def test_stronger_team_gets_higher_xg_at_home(fitted_model: TeamStrengthModel) -> None:
    strong_home_xg, weak_away_xg = fitted_model.expected_goals("STR", "WEAK", is_neutral=False)
    weak_home_xg, strong_away_xg = fitted_model.expected_goals("WEAK", "STR", is_neutral=False)

    assert strong_home_xg > weak_home_xg
    assert strong_away_xg > weak_away_xg
    assert fitted_model.get_team_params("STR")["attack"] > fitted_model.get_team_params("WEAK")["attack"]
    assert fitted_model.get_team_params("STR")["defense"] > fitted_model.get_team_params("WEAK")["defense"]


def test_neutral_venue_reduces_home_xg(fitted_model: TeamStrengthModel) -> None:
    home_xg_with_adv, _ = fitted_model.expected_goals("STR", "WEAK", is_neutral=False)
    home_xg_neutral, _ = fitted_model.expected_goals("STR", "WEAK", is_neutral=True)

    assert home_xg_neutral < home_xg_with_adv


def test_unknown_team_uses_competition_average(fitted_model: TeamStrengthModel) -> None:
    home_xg, away_xg = fitted_model.expected_goals("STR", "UNKNOWN_TEAM", is_neutral=False)
    unknown_params = fitted_model.get_team_params("UNKNOWN_TEAM")
    known_attacks = [
        fitted_model.get_team_params(team_id)["attack"]
        for team_id in fitted_model.team_params
    ]
    known_defenses = [
        fitted_model.get_team_params(team_id)["defense"]
        for team_id in fitted_model.team_params
    ]
    expected_attack = sum(known_attacks) / len(known_attacks)
    expected_defense = sum(known_defenses) / len(known_defenses)

    assert unknown_params["matches_played"] == 0
    assert unknown_params["attack"] == pytest.approx(expected_attack)
    assert unknown_params["defense"] == pytest.approx(expected_defense)
    assert 0.15 <= home_xg <= 3.8
    assert 0.15 <= away_xg <= 3.8


def test_predict_fixture_marks_world_cup_as_neutral(fitted_model: TeamStrengthModel) -> None:
    fixture = Fixture(
        fixture_id="wc-test",
        home_team_id="STR",
        away_team_id="WEAK",
        home_team_name="Strongland",
        away_team_name="Weakland",
        kickoff_utc=BASE_DATE,
        status="scheduled",
        competition="FIFA World Cup 2026",
        stage="Group A - 1",
        venue="Test Stadium",
        home_goals=None,
        away_goals=None,
    )
    prediction = fitted_model.predict_fixture(fixture)

    assert prediction["is_neutral"] is True
    assert prediction["home_advantage_applied"] == 0.0
    assert prediction["home_xg"] == pytest.approx(
        fitted_model.expected_goals("STR", "WEAK", is_neutral=True)[0],
    )


def test_from_results_convenience_constructor() -> None:
    model = TeamStrengthModel.from_results(_build_synthetic_results())
    assert model.is_fitted
    assert len(model.team_params) >= 7


def test_fit_empty_results_does_not_crash() -> None:
    model = TeamStrengthModel()
    model.fit([])
    home_xg, away_xg = model.expected_goals("A", "B", is_neutral=False)
    assert 0.15 <= home_xg <= 3.8
    assert 0.15 <= away_xg <= 3.8


def test_clamp_xg_bounds() -> None:
    assert clamp_xg(0.01) == 0.15
    assert clamp_xg(10.0) == 3.8
    assert clamp_xg(1.5) == 1.5


@pytest.mark.asyncio
async def test_prediction_service_compute_base_xg() -> None:
    from fifa26_engine.data.mock_provider import MockFixtureProvider
    from fifa26_engine.services.prediction_service import PredictionService

    provider = MockFixtureProvider()
    service = PredictionService(provider=provider)
    fixture = await provider.get_fixture_by_id("wc26-005")
    assert fixture is not None

    prediction = await service.compute_base_xg(fixture)
    assert 0.15 <= prediction["home_xg"] <= 3.8
    assert 0.15 <= prediction["away_xg"] <= 3.8
    assert prediction["is_neutral"] is True
