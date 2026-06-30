"""Knockout-stage markets: regulation 1X2 and to-advance probabilities."""

from __future__ import annotations

from dataclasses import dataclass

from fifa26_engine.models.simulator import MatchSimulator

ET_DURATION_FACTOR = 30.0 / 90.0
ET_XG_BOOST = 1.08
PENALTY_EDGE_SCALE = 0.10


@dataclass(frozen=True)
class KnockoutMarkets:
    """Regulation and advancement probabilities for knockout fixtures."""

    regulation_home_win: float
    regulation_draw: float
    regulation_away_win: float
    advance_home: float
    advance_away: float


def _penalty_home_win_prob(home_xg: float, away_xg: float) -> float:
    total = max(home_xg + away_xg, 0.01)
    edge = PENALTY_EDGE_SCALE * (home_xg - away_xg) / total
    return max(0.35, min(0.65, 0.5 + edge))


def compute_knockout_markets(
    home_xg: float,
    away_xg: float,
    *,
    max_goals: int = 10,
    dixon_coles_rho: float = -0.13,
) -> KnockoutMarkets:
    """Derive regulation 1X2 and to-advance markets from adjusted xG."""
    regulation = MatchSimulator(
        home_xg=home_xg,
        away_xg=away_xg,
        max_goals=max_goals,
        dixon_coles_rho=dixon_coles_rho,
    ).simulate()
    reg = regulation.markets

    et_home = home_xg * ET_XG_BOOST * ET_DURATION_FACTOR
    et_away = away_xg * ET_XG_BOOST * ET_DURATION_FACTOR
    extra_time = MatchSimulator(
        home_xg=et_home,
        away_xg=et_away,
        max_goals=6,
        dixon_coles_rho=dixon_coles_rho,
    ).simulate()
    et = extra_time.markets

    pen_home = _penalty_home_win_prob(home_xg, away_xg)
    home_adv_if_draw = et["home_win"] + et["draw"] * pen_home

    advance_home = reg["home_win"] + reg["draw"] * home_adv_if_draw
    advance_away = 1.0 - advance_home

    return KnockoutMarkets(
        regulation_home_win=reg["home_win"],
        regulation_draw=reg["draw"],
        regulation_away_win=reg["away_win"],
        advance_home=advance_home,
        advance_away=advance_away,
    )
