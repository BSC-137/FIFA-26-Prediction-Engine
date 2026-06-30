"""Lightweight Elo ratings fitted from tournament match results only."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from fifa26_engine.data.provider import MatchResult

DEFAULT_ELO = 1500.0
DEFAULT_K = 32.0
GOAL_SCALE = 400.0


def _ensure_aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


class EloPrior:
    """Elo ratings and implied xG from chronological match results."""

    def __init__(self, k_factor: float = DEFAULT_K) -> None:
        self._k = k_factor
        self._ratings: dict[str, float] = {}
        self._avg_goals_per_team: float = 1.35
        self._is_fitted = False

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    @property
    def ratings(self) -> dict[str, float]:
        return dict(self._ratings)

    def fit(self, results: list[MatchResult]) -> None:
        """Update Elo ratings from finished matches in chronological order."""
        if not results:
            self._ratings = {}
            self._avg_goals_per_team = 1.35
            self._is_fitted = False
            return

        ordered = sorted(results, key=lambda match: _ensure_aware(match.date))
        total_goals = sum(match.home_goals + match.away_goals for match in ordered)
        self._avg_goals_per_team = max(0.5, total_goals / (2 * len(ordered)))

        ratings: dict[str, float] = {}
        for match in ordered:
            home_id = match.home_team_id
            away_id = match.away_team_id
            home_elo = ratings.get(home_id, DEFAULT_ELO)
            away_elo = ratings.get(away_id, DEFAULT_ELO)

            expected_home = 1.0 / (1.0 + 10.0 ** ((away_elo - home_elo) / GOAL_SCALE))
            if match.home_goals > match.away_goals:
                score_home = 1.0
            elif match.home_goals < match.away_goals:
                score_home = 0.0
            else:
                score_home = 0.5

            delta = self._k * (score_home - expected_home)
            ratings[home_id] = home_elo + delta
            ratings[away_id] = away_elo - delta

        self._ratings = ratings
        self._is_fitted = True

    def expected_goals(self, home_team_id: str, away_team_id: str) -> tuple[float, float]:
        """Map Elo difference to implied Poisson rates."""
        home_elo = self._ratings.get(home_team_id, DEFAULT_ELO)
        away_elo = self._ratings.get(away_team_id, DEFAULT_ELO)
        diff = home_elo - away_elo
        home_share = 1.0 / (1.0 + 10.0 ** (-diff / GOAL_SCALE))
        total = self._avg_goals_per_team * 2.0
        home_xg = total * home_share
        away_xg = total * (1.0 - home_share)
        return home_xg, away_xg

    @staticmethod
    def blend(
        poisson_home: float,
        poisson_away: float,
        elo_home: float,
        elo_away: float,
        weight: float,
    ) -> tuple[float, float]:
        """Blend Poisson xG with Elo-implied xG."""
        if weight <= 0.0:
            return poisson_home, poisson_away
        w = min(1.0, weight)
        return (
            (1.0 - w) * poisson_home + w * elo_home,
            (1.0 - w) * poisson_away + w * elo_away,
        )
