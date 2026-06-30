"""Post-strength calibration: Elo blend, tournament floor, diagnostics."""

from __future__ import annotations

from fifa26_engine.config.model_config import ModelConfig
from fifa26_engine.data.provider import Fixture, MatchResult
from fifa26_engine.data.stadiums import resolve_stadium
from fifa26_engine.models.elo_prior import EloPrior
from fifa26_engine.models.strength import FixturePrediction, TeamStrengthModel, infer_fixture_is_neutral

WC2026_HOST_NATIONS = frozenset({"mexico", "united-states", "canada"})


def is_world_cup_competition(competition: str) -> bool:
    return "world cup" in competition.lower()


def count_team_matches(results: list[MatchResult], team_id: str) -> int:
    count = 0
    for result in results:
        if result.home_team_id == team_id or result.away_team_id == team_id:
            count += 1
    return count


def apply_host_boost(
    home_xg: float,
    away_xg: float,
    fixture: Fixture,
    host_boost: float,
) -> tuple[float, float, float]:
    """Apply a small log-rate boost for 2026 host nations."""
    if host_boost <= 0.0 or not is_world_cup_competition(fixture.competition):
        return home_xg, away_xg, 0.0

    import math

    from fifa26_engine.models.strength import clamp_xg

    applied = 0.0
    if fixture.home_team_id in WC2026_HOST_NATIONS:
        home_xg = clamp_xg(math.exp(math.log(max(home_xg, 0.01)) + host_boost))
        applied = host_boost
    elif fixture.away_team_id in WC2026_HOST_NATIONS:
        away_xg = clamp_xg(math.exp(math.log(max(away_xg, 0.01)) + host_boost))
        applied = host_boost
    return home_xg, away_xg, applied


def apply_tournament_scoring_floor(
    home_xg: float,
    away_xg: float,
    *,
    is_neutral: bool,
    floor: float,
) -> tuple[float, float, bool]:
    """Scale xG up proportionally when total raw rate is below the tournament floor."""
    if floor <= 0.0 or not is_neutral:
        return home_xg, away_xg, False
    total = home_xg + away_xg
    if total >= floor or total <= 0.0:
        return home_xg, away_xg, False
    scale = floor / total
    return home_xg * scale, away_xg * scale, True


def calibrate_base_xg(
    prediction: FixturePrediction,
    fixture: Fixture,
    results: list[MatchResult],
    model_config: ModelConfig,
) -> tuple[float, float, list[str], float]:
    """Blend Elo, apply host boost and tournament floor; return labels."""
    labels: list[str] = []
    home_xg = prediction["home_xg"]
    away_xg = prediction["away_xg"]

    if model_config.elo_blend_weight > 0.0 and results:
        elo = EloPrior()
        elo.fit(results)
        elo_home, elo_away = elo.expected_goals(fixture.home_team_id, fixture.away_team_id)
        home_xg, away_xg = EloPrior.blend(
            home_xg,
            away_xg,
            elo_home,
            elo_away,
            model_config.elo_blend_weight,
        )
        labels.append(f"elo_blend:{model_config.elo_blend_weight:.2f}")

    home_xg, away_xg, host_applied = apply_host_boost(
        home_xg,
        away_xg,
        fixture,
        model_config.host_nation_boost,
    )
    if host_applied > 0.0:
        labels.append(f"host_nation_boost:{host_applied:.2f}")

    home_xg, away_xg, floor_applied = apply_tournament_scoring_floor(
        home_xg,
        away_xg,
        is_neutral=prediction["is_neutral"],
        floor=model_config.tournament_min_total_xg,
    )
    if floor_applied:
        labels.append("tournament_scoring_floor_applied")

    return home_xg, away_xg, labels, host_applied


def build_prediction_warnings(
    *,
    adjusted_home_xg: float,
    adjusted_away_xg: float,
    draw_probability: float,
    home_wc_matches: int,
    away_wc_matches: int,
    fixture: Fixture,
) -> list[str]:
    """Auto-generate transparency warnings for low-confidence predictions."""
    warnings: list[str] = []
    if adjusted_home_xg + adjusted_away_xg < 1.2:
        warnings.append("low_total_xg")
    if draw_probability > 0.45:
        warnings.append("high_draw_probability")
    if home_wc_matches < 2:
        warnings.append("home_sparse_wc_history")
    if away_wc_matches < 2:
        warnings.append("away_sparse_wc_history")
    stadium = resolve_stadium(fixture)
    if stadium.lat is None:
        warnings.append("venue_resolution_unknown")
    return warnings
