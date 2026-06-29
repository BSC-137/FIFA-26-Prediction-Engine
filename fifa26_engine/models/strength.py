"""Poisson attack/defense team strength model for expected goals (xG).

Model assumptions
-----------------
* Goals follow independent Poisson processes (correlation handled later in simulator).
* Log-rate for the home side::

      log(λ_home) = μ + attack_home − defense_away + α · I(not neutral)

* Log-rate for the away side::

      log(λ_away) = μ + attack_away − defense_home

* ``μ`` is a global intercept (baseline scoring rate).
* ``α`` is a global home-advantage parameter, applied only at non-neutral venues.
* Attack/defense ratings are mean-centred across teams for identifiability.
* Teams with few observed matches are shrunk toward the league average (0 attack, 0 defense).
* Unknown teams at prediction time use the league-average rating (no crash).

Fitting uses penalised negative log-likelihood minimisation (L-BFGS-B).
The public API is stable for downstream simulator and adjustment layers.
"""

from __future__ import annotations

import math
from typing import Any, TypedDict

import numpy as np
from scipy.optimize import minimize

from fifa26_engine.data.provider import Fixture, MatchResult

XG_MIN = 0.15
XG_MAX = 3.8
DEFAULT_SHRINKAGE_PRIOR_MATCHES = 8.0
DEFAULT_HOME_ADVANTAGE = 0.22
NEUTRAL_COMPETITION_KEYWORDS = ("world cup", "euro", "copa america", "nations league finals")


class TeamParams(TypedDict):
    """Fitted strength metadata for one team."""

    attack: float
    defense: float
    matches_played: int


class FixturePrediction(TypedDict):
    """xG prediction payload for a single fixture."""

    home_xg: float
    away_xg: float
    home_attack: float
    away_attack: float
    home_defense: float
    away_defense: float
    home_advantage_applied: float
    is_neutral: bool


def clamp_xg(value: float) -> float:
    """Clamp an expected-goals value to sensible bounds."""
    return max(XG_MIN, min(XG_MAX, value))


def infer_fixture_is_neutral(fixture: Fixture) -> bool:
    """Infer whether a fixture should be treated as a neutral venue.

    World Cup and other major tournaments are modelled as neutral because
    designated home/away labels rarely reflect true home advantage.
    """
    competition = fixture.competition.lower()
    return any(keyword in competition for keyword in NEUTRAL_COMPETITION_KEYWORDS)


class TeamStrengthModel:
    """Poisson attack/defense ratings with home advantage and shrinkage."""

    def __init__(
        self,
        shrinkage_prior_matches: float = DEFAULT_SHRINKAGE_PRIOR_MATCHES,
        xg_min: float = XG_MIN,
        xg_max: float = XG_MAX,
    ) -> None:
        """Initialise an unfitted model."""
        self._shrinkage_prior = max(0.0, shrinkage_prior_matches)
        self._xg_min = xg_min
        self._xg_max = xg_max
        self._intercept: float = math.log(1.35)
        self._home_advantage: float = DEFAULT_HOME_ADVANTAGE
        self._teams: list[str] = []
        self._team_index: dict[str, int] = {}
        self._raw_attack: np.ndarray = np.array([])
        self._raw_defense: np.ndarray = np.array([])
        self._team_params: dict[str, TeamParams] = {}
        self._is_fitted = False

    @property
    def is_fitted(self) -> bool:
        """Return True after ``fit`` has been called successfully."""
        return self._is_fitted

    @property
    def home_advantage(self) -> float:
        """Global fitted home-advantage parameter (log-rate scale)."""
        return self._home_advantage

    @property
    def intercept(self) -> float:
        """Global fitted intercept (log-rate scale)."""
        return self._intercept

    @property
    def team_params(self) -> dict[str, TeamParams]:
        """Shrunk team metadata keyed by team ID."""
        return dict(self._team_params)

    @staticmethod
    def from_results(results: list[MatchResult]) -> TeamStrengthModel:
        """Convenience constructor: create and fit a model in one step."""
        model = TeamStrengthModel()
        model.fit(results)
        return model

    def fit(self, results: list[MatchResult]) -> None:
        """Fit attack/defense parameters from historical match results.

        Args:
            results: Finished matches with goals and venue neutrality flags.
        """
        if not results:
            self._reset_to_prior()
            return

        teams, matches_played = self._collect_teams(results)
        self._teams = teams
        self._team_index = {team_id: index for index, team_id in enumerate(teams)}
        n_teams = len(teams)

        home_idx = np.array([self._team_index[match.home_team_id] for match in results])
        away_idx = np.array([self._team_index[match.away_team_id] for match in results])
        home_goals = np.array([match.home_goals for match in results], dtype=float)
        away_goals = np.array([match.away_goals for match in results], dtype=float)
        is_neutral = np.array([match.is_neutral for match in results], dtype=bool)

        initial = self._initial_parameters(n_teams, home_goals, away_goals)
        bounds = self._parameter_bounds(n_teams)

        def objective(params: np.ndarray) -> float:
            return self._negative_log_likelihood(
                params,
                home_idx,
                away_idx,
                home_goals,
                away_goals,
                is_neutral,
                n_teams,
            )

        result = minimize(
            objective,
            initial,
            method="L-BFGS-B",
            bounds=bounds,
            options={"maxiter": 500, "ftol": 1e-9},
        )

        self._unpack_parameters(result.x, n_teams)
        self._apply_shrinkage(matches_played)
        self._is_fitted = True

    def get_team_params(self, team_id: str) -> TeamParams:
        """Return shrunk parameters for a team, or league average if unknown."""
        if team_id in self._team_params:
            return self._team_params[team_id]
        return TeamParams(attack=0.0, defense=0.0, matches_played=0)

    def expected_goals(
        self,
        home_team_id: str,
        away_team_id: str,
        is_neutral: bool = False,
    ) -> tuple[float, float]:
        """Return ``(home_xg, away_xg)`` from fitted parameters."""
        home = self.get_team_params(home_team_id)
        away = self.get_team_params(away_team_id)

        home_adv = 0.0 if is_neutral else self._home_advantage
        log_home = (
            self._intercept + home["attack"] - away["defense"] + home_adv
        )
        log_away = self._intercept + away["attack"] - home["defense"]

        return (
            clamp_xg(math.exp(log_home)),
            clamp_xg(math.exp(log_away)),
        )

    def predict_fixture(self, fixture: Fixture) -> FixturePrediction:
        """Predict base xG and expose rating components for a fixture."""
        is_neutral = infer_fixture_is_neutral(fixture)
        home = self.get_team_params(fixture.home_team_id)
        away = self.get_team_params(fixture.away_team_id)
        home_adv_applied = 0.0 if is_neutral else self._home_advantage
        home_xg, away_xg = self.expected_goals(
            fixture.home_team_id,
            fixture.away_team_id,
            is_neutral=is_neutral,
        )

        return FixturePrediction(
            home_xg=home_xg,
            away_xg=away_xg,
            home_attack=home["attack"],
            away_attack=away["attack"],
            home_defense=home["defense"],
            away_defense=away["defense"],
            home_advantage_applied=home_adv_applied,
            is_neutral=is_neutral,
        )

    def _reset_to_prior(self) -> None:
        self._teams = []
        self._team_index = {}
        self._raw_attack = np.array([])
        self._raw_defense = np.array([])
        self._team_params = {}
        self._intercept = math.log(1.35)
        self._home_advantage = DEFAULT_HOME_ADVANTAGE
        self._is_fitted = False

    @staticmethod
    def _collect_teams(results: list[MatchResult]) -> tuple[list[str], dict[str, int]]:
        matches_played: dict[str, int] = {}
        for match in results:
            matches_played[match.home_team_id] = matches_played.get(match.home_team_id, 0) + 1
            matches_played[match.away_team_id] = matches_played.get(match.away_team_id, 0) + 1
        teams = sorted(matches_played)
        return teams, matches_played

    def _initial_parameters(
        self,
        n_teams: int,
        home_goals: np.ndarray,
        away_goals: np.ndarray,
    ) -> np.ndarray:
        mean_rate = max(0.5, float(np.mean(np.concatenate([home_goals, away_goals]))))
        intercept = math.log(mean_rate)
        attacks = np.zeros(n_teams)
        defenses = np.zeros(n_teams)
        return np.concatenate([[intercept, DEFAULT_HOME_ADVANTAGE], attacks, defenses])

    @staticmethod
    def _parameter_bounds(n_teams: int) -> list[tuple[float | None, float | None]]:
        bounds: list[tuple[float | None, float | None]] = [
            (-2.0, 2.0),  # intercept
            (0.0, 1.0),  # home advantage
        ]
        bounds.extend([(-2.5, 2.5)] * n_teams)  # attacks
        bounds.extend([(-2.5, 2.5)] * n_teams)  # defenses
        return bounds

    def _negative_log_likelihood(
        self,
        params: np.ndarray,
        home_idx: np.ndarray,
        away_idx: np.ndarray,
        home_goals: np.ndarray,
        away_goals: np.ndarray,
        is_neutral: np.ndarray,
        n_teams: int,
    ) -> float:
        intercept = params[0]
        home_adv = params[1]
        attacks = params[2 : 2 + n_teams]
        defenses = params[2 + n_teams : 2 + 2 * n_teams]

        home_attack = attacks[home_idx]
        away_attack = attacks[away_idx]
        home_defense = defenses[home_idx]
        away_defense = defenses[away_idx]

        home_log_rate = intercept + home_attack - away_defense
        home_log_rate = np.where(is_neutral, home_log_rate, home_log_rate + home_adv)
        away_log_rate = intercept + away_attack - home_defense

        # Stable Poisson NLL: λ - g*log(λ) with λ = exp(log_λ)
        home_nll = np.exp(home_log_rate) - home_goals * home_log_rate
        away_nll = np.exp(away_log_rate) - away_goals * away_log_rate
        nll = float(np.sum(home_nll + away_nll))

        # Soft identifiability constraints (mean-zero attack/defense).
        nll += 50.0 * float(attacks.mean() ** 2 + defenses.mean() ** 2)
        return nll

    def _unpack_parameters(self, params: np.ndarray, n_teams: int) -> None:
        self._intercept = float(params[0])
        self._home_advantage = float(params[1])
        self._raw_attack = params[2 : 2 + n_teams].copy()
        self._raw_defense = params[2 + n_teams : 2 + 2 * n_teams].copy()

        # Re-centre for reporting consistency.
        attack_mean = float(self._raw_attack.mean())
        defense_mean = float(self._raw_defense.mean())
        self._intercept += attack_mean - defense_mean
        self._raw_attack -= attack_mean
        self._raw_defense -= defense_mean

    def _apply_shrinkage(self, matches_played: dict[str, int]) -> None:
        self._team_params = {}
        for index, team_id in enumerate(self._teams):
            n = matches_played[team_id]
            weight = n / (n + self._shrinkage_prior) if self._shrinkage_prior > 0 else 1.0
            self._team_params[team_id] = TeamParams(
                attack=float(self._raw_attack[index] * weight),
                defense=float(self._raw_defense[index] * weight),
                matches_played=n,
            )
