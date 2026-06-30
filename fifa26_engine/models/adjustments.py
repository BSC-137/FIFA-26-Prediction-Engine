"""Structured, explainable match-context adjustments.

Applies small multiplicative factors for injuries, rest, knockout pressure, and
weather affinity modifiers. Each factor is clamped individually; total deviation
from baseline xG is capped at ±8%.
"""

from __future__ import annotations

from dataclasses import dataclass

from fifa26_engine.data.provider import PitchType, WeatherConditions
from fifa26_engine.models.strength import clamp_xg

FACTOR_MIN = 0.92
FACTOR_MAX = 1.08
TOTAL_ADJUSTMENT_CAP = 0.08
MISSING_PLAYER_PENALTY = 0.025
SHORT_REST_THRESHOLD_DAYS = 4
SHORT_REST_PENALTY = 0.03
LONG_REST_THRESHOLD_DAYS = 6
LONG_REST_BONUS = 0.015
KNOCKOUT_DEFENSIVE_FACTOR = 0.97


@dataclass(frozen=True)
class MatchContext:
    """Structured context inputs for adjustment layers."""

    home_missing_key_players: int = 0
    away_missing_key_players: int = 0
    home_days_rest: int | None = None
    away_days_rest: int | None = None
    is_knockout: bool = False
    weather: WeatherConditions | None = None
    pitch_type: PitchType = "unknown"


def _clamp_factor(value: float) -> float:
    return max(FACTOR_MIN, min(FACTOR_MAX, value))


def _apply_total_cap(home_xg: float, away_xg: float, base_home: float, base_away: float) -> tuple[float, float]:
    """Ensure combined adjustment vs base xG stays within ±8%."""
    base_total = base_home + base_away
    if base_total <= 0:
        return home_xg, away_xg
    adjusted_total = home_xg + away_xg
    max_total = base_total * (1.0 + TOTAL_ADJUSTMENT_CAP)
    min_total = base_total * (1.0 - TOTAL_ADJUSTMENT_CAP)
    if min_total <= adjusted_total <= max_total:
        return home_xg, away_xg
    target_total = max(min_total, min(max_total, adjusted_total))
    scale = target_total / adjusted_total
    return home_xg * scale, away_xg * scale


class AdjustmentEngine:
    """Apply transparent multiplicative context adjustments to xG."""

    def apply(
        self,
        home_xg: float,
        away_xg: float,
        context: MatchContext,
        weather_modifiers: tuple[float, float, list[str]] | None = None,
    ) -> tuple[float, float, list[str]]:
        """Return adjusted ``(home_xg, away_xg)`` and human-readable labels."""
        labels: list[str] = []
        home_factor = 1.0
        away_factor = 1.0

        if weather_modifiers is not None:
            weather_home, weather_away, weather_labels = weather_modifiers
            home_factor *= weather_home
            away_factor *= weather_away
            labels.extend(weather_labels)

        if context.home_missing_key_players > 0:
            penalty = _clamp_factor(1.0 - MISSING_PLAYER_PENALTY * context.home_missing_key_players)
            home_factor *= penalty
            labels.append(f"home_missing_players:{context.home_missing_key_players}")

        if context.away_missing_key_players > 0:
            penalty = _clamp_factor(1.0 - MISSING_PLAYER_PENALTY * context.away_missing_key_players)
            away_factor *= penalty
            labels.append(f"away_missing_players:{context.away_missing_key_players}")

        if context.home_days_rest is not None:
            if context.home_days_rest < SHORT_REST_THRESHOLD_DAYS:
                home_factor *= _clamp_factor(1.0 - SHORT_REST_PENALTY)
                labels.append(f"home_short_rest:{context.home_days_rest}d")
            elif context.home_days_rest > LONG_REST_THRESHOLD_DAYS:
                home_factor *= _clamp_factor(1.0 + LONG_REST_BONUS)
                labels.append(f"home_long_rest:{context.home_days_rest}d")

        if context.away_days_rest is not None:
            if context.away_days_rest < SHORT_REST_THRESHOLD_DAYS:
                away_factor *= _clamp_factor(1.0 - SHORT_REST_PENALTY)
                labels.append(f"away_short_rest:{context.away_days_rest}d")
            elif context.away_days_rest > LONG_REST_THRESHOLD_DAYS:
                away_factor *= _clamp_factor(1.0 + LONG_REST_BONUS)
                labels.append(f"away_long_rest:{context.away_days_rest}d")

        # Knockout defensive adjustment removed — knockout markets handled in knockout.py.

        home_factor = _clamp_factor(home_factor)
        away_factor = _clamp_factor(away_factor)

        base_home, base_away = home_xg, away_xg
        adjusted_home = clamp_xg(home_xg * home_factor)
        adjusted_away = clamp_xg(away_xg * away_factor)
        adjusted_home, adjusted_away = _apply_total_cap(adjusted_home, adjusted_away, base_home, base_away)
        adjusted_home = clamp_xg(adjusted_home)
        adjusted_away = clamp_xg(adjusted_away)

        return adjusted_home, adjusted_away, labels
