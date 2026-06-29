"""Vectorized Poisson score-matrix simulation with Dixon–Coles adjustment.

Given expected goals (λ_home, λ_away) from the strength model, this module builds
an exact score probability matrix, applies low-score correlation (Dixon–Coles τ),
and aggregates standard betting markets (1X2, BTTS, totals, top correct scores).

Assumptions
-----------
* Marginal goal counts are Poisson with rates λ_home and λ_away before DC adjustment.
* Dixon–Coles ρ corrects dependence for 0–0, 1–0, 0–1, and 1–1 cells only.
* Truncation at ``max_goals`` introduces negligible mass loss for typical NT xG values.
* No extra-time or penalty modelling (group / regulation-time markets only).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

import numpy as np
from scipy.stats import poisson

DEFAULT_MAX_GOALS = 10
DEFAULT_DIXON_COLES_RHO = -0.13


class TopScore(TypedDict):
    """A single entry in the top-scores market list."""

    score: str
    probability: float


class MarketProbabilities(TypedDict):
    """Aggregated market probabilities from a score matrix."""

    home_win: float
    draw: float
    away_win: float
    btts_yes: float
    btts_no: float
    over_1_5: float
    under_1_5: float
    over_2_5: float
    under_2_5: float
    over_3_5: float
    under_3_5: float
    top_scores: list[TopScore]


@dataclass(frozen=True)
class SimulationResult:
    """Full simulation output for a single fixture."""

    home_xg: float
    away_xg: float
    matrix: np.ndarray
    markets: MarketProbabilities
    dixon_coles_rho: float


class MatchSimulator:
    """Vectorized match simulator from expected goals to market probabilities."""

    def __init__(
        self,
        home_xg: float,
        away_xg: float,
        max_goals: int = DEFAULT_MAX_GOALS,
        dixon_coles_rho: float = DEFAULT_DIXON_COLES_RHO,
    ) -> None:
        """Initialise simulator parameters.

        Args:
            home_xg: Expected home goals (Poisson rate).
            away_xg: Expected away goals (Poisson rate).
            max_goals: Matrix dimension; scores run from 0 to ``max_goals - 1``.
            dixon_coles_rho: Dixon–Coles low-score correlation parameter.
        """
        if max_goals < 2:
            raise ValueError("max_goals must be at least 2")
        self.home_xg = home_xg
        self.away_xg = away_xg
        self.max_goals = max_goals
        self.dixon_coles_rho = dixon_coles_rho

    def score_matrix(self) -> np.ndarray:
        """Return independent Poisson score probability matrix (home × away)."""
        goals = np.arange(self.max_goals)
        home_pmf = poisson.pmf(goals, self.home_xg)
        away_pmf = poisson.pmf(goals, self.away_xg)
        return np.outer(home_pmf, away_pmf)

    def apply_dixon_coles(self, matrix: np.ndarray) -> np.ndarray:
        """Apply Dixon–Coles τ adjustment to low-score cells and renormalise."""
        if matrix.shape != (self.max_goals, self.max_goals):
            raise ValueError(
                f"matrix shape {matrix.shape} does not match "
                f"({self.max_goals}, {self.max_goals})",
            )

        rho = self.dixon_coles_rho
        lam_home = self.home_xg
        lam_away = self.away_xg

        tau = np.ones_like(matrix, dtype=float)
        tau[0, 0] = 1.0 - lam_home * lam_away * rho
        tau[0, 1] = 1.0 + lam_home * rho
        tau[1, 0] = 1.0 + lam_away * rho
        tau[1, 1] = 1.0 - rho

        adjusted = matrix * tau
        total = adjusted.sum()
        if total <= 0.0:
            raise ValueError("Dixon–Coles adjustment produced non-positive matrix mass")
        return adjusted / total

    def markets(self, matrix: np.ndarray) -> MarketProbabilities:
        """Aggregate standard market probabilities from a score matrix."""
        home_goals = np.arange(self.max_goals)[:, np.newaxis]
        away_goals = np.arange(self.max_goals)[np.newaxis, :]
        total_goals = home_goals + away_goals

        home_win = float(matrix[home_goals > away_goals].sum())
        draw = float(matrix[home_goals == away_goals].sum())
        away_win = float(matrix[home_goals < away_goals].sum())

        btts_yes = float(matrix[(home_goals > 0) & (away_goals > 0)].sum())
        btts_no = 1.0 - btts_yes

        over_1_5 = float(matrix[total_goals > 1.5].sum())
        over_2_5 = float(matrix[total_goals > 2.5].sum())
        over_3_5 = float(matrix[total_goals > 3.5].sum())

        top_scores = self._top_scores(matrix, limit=5)

        return MarketProbabilities(
            home_win=home_win,
            draw=draw,
            away_win=away_win,
            btts_yes=btts_yes,
            btts_no=btts_no,
            over_1_5=over_1_5,
            under_1_5=1.0 - over_1_5,
            over_2_5=over_2_5,
            under_2_5=1.0 - over_2_5,
            over_3_5=over_3_5,
            under_3_5=1.0 - over_3_5,
            top_scores=top_scores,
        )

    def most_likely_1x2_outcome(self, matrix: np.ndarray) -> str:
        """Return the highest-probability 1X2 outcome key."""
        market = self.markets(matrix)
        outcomes = {
            "home_win": market["home_win"],
            "draw": market["draw"],
            "away_win": market["away_win"],
        }
        return max(outcomes, key=outcomes.get)  # type: ignore[arg-type]

    def simulate(self) -> SimulationResult:
        """Build matrix, apply Dixon–Coles, and return full simulation output."""
        raw = self.score_matrix()
        adjusted = self.apply_dixon_coles(raw)
        market_probs = self.markets(adjusted)
        return SimulationResult(
            home_xg=self.home_xg,
            away_xg=self.away_xg,
            matrix=adjusted,
            markets=market_probs,
            dixon_coles_rho=self.dixon_coles_rho,
        )

    @staticmethod
    def _top_scores(matrix: np.ndarray, limit: int = 5) -> list[TopScore]:
        """Return the ``limit`` most likely exact scorelines."""
        flat = matrix.ravel()
        if limit <= 0:
            return []
        top_indices = np.argpartition(-flat, min(limit, flat.size) - 1)[:limit]
        top_indices = top_indices[np.argsort(-flat[top_indices])]

        n_cols = matrix.shape[1]
        scores: list[TopScore] = []
        for flat_index in top_indices:
            home = int(flat_index // n_cols)
            away = int(flat_index % n_cols)
            scores.append(
                TopScore(
                    score=f"{home}-{away}",
                    probability=float(flat[flat_index]),
                ),
            )
        return scores
