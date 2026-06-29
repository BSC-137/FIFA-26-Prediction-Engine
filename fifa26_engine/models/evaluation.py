"""Leakage-safe accuracy evaluation from stored pre-kickoff predictions.

Evaluation NEVER refits models or generates new predictions for finished fixtures.
It only compares ledger rows (frozen at as_of_utc <= kickoff) to actual results.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fifa26_engine.data.provider import Fixture
from fifa26_engine.storage.prediction_store import PredictionRecord

Outcome = str  # home_win | draw | away_win


@dataclass(frozen=True)
class CalibrationBin:
    """Home-win probability calibration bucket."""

    bin_start: float
    bin_end: float
    count: int
    mean_predicted: float
    actual_rate: float


@dataclass(frozen=True)
class EvaluatedFixture:
    """Stored prediction compared to an actual finished result."""

    fixture_id: str
    home_team_id: str
    away_team_id: str
    kickoff_utc: datetime
    as_of_utc: datetime
    predicted_outcome: Outcome
    actual_outcome: Outcome
    correct_1x2: bool
    p_home: float
    p_draw: float
    p_away: float
    actual_home_goals: int
    actual_away_goals: int
    expected_total_goals: float
    actual_total_goals: int
    brier: float
    log_loss: float
    total_goals_error: float


@dataclass
class EvaluationSummary:
    """Aggregate accuracy metrics over evaluated fixtures."""

    n_matches: int
    accuracy_1x2: float
    brier_score: float
    log_loss: float
    mae_total_goals: float
    calibration_bins: list[CalibrationBin] = field(default_factory=list)
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    model_version: str = ""


def _outcome(home_goals: int, away_goals: int) -> Outcome:
    if home_goals > away_goals:
        return "home_win"
    if home_goals < away_goals:
        return "away_win"
    return "draw"


def _argmax_outcome(p_home: float, p_draw: float, p_away: float) -> Outcome:
    outcomes = {"home_win": p_home, "draw": p_draw, "away_win": p_away}
    return max(outcomes, key=outcomes.get)  # type: ignore[arg-type]


def _brier(p_home: float, p_draw: float, p_away: float, actual: Outcome) -> float:
    actuals = {
        "home_win": 1.0 if actual == "home_win" else 0.0,
        "draw": 1.0 if actual == "draw" else 0.0,
        "away_win": 1.0 if actual == "away_win" else 0.0,
    }
    return (
        (p_home - actuals["home_win"]) ** 2
        + (p_draw - actuals["draw"]) ** 2
        + (p_away - actuals["away_win"]) ** 2
    )


def _log_loss(p_home: float, p_draw: float, p_away: float, actual: Outcome) -> float:
    probs = {"home_win": p_home, "draw": p_draw, "away_win": p_away}
    prob = max(probs[actual], 1e-15)
    return -math.log(prob)


def _calibration_bins(
    pairs: list[tuple[float, float]],
    n_bins: int = 5,
) -> list[CalibrationBin]:
    if not pairs:
        return []
    bins: list[CalibrationBin] = []
    for index in range(n_bins):
        start = index / n_bins
        end = (index + 1) / n_bins
        bucket = [(pred, actual) for pred, actual in pairs if start <= pred < end or (index == n_bins - 1 and pred == 1.0)]
        if not bucket:
            bins.append(CalibrationBin(start, end, 0, 0.0, 0.0))
            continue
        mean_pred = sum(item[0] for item in bucket) / len(bucket)
        actual_rate = sum(item[1] for item in bucket) / len(bucket)
        bins.append(CalibrationBin(start, end, len(bucket), mean_pred, actual_rate))
    return bins


def evaluate_fixture(
    record: PredictionRecord,
    fixture: Fixture,
) -> EvaluatedFixture | None:
    """Evaluate one stored prediction against a finished fixture."""
    if fixture.home_goals is None or fixture.away_goals is None:
        return None
    if fixture.status != "finished":
        return None

    actual = _outcome(fixture.home_goals, fixture.away_goals)
    predicted = _argmax_outcome(record.p_home, record.p_draw, record.p_away)
    expected_total = record.adj_home_xg + record.adj_away_xg
    actual_total = fixture.home_goals + fixture.away_goals

    return EvaluatedFixture(
        fixture_id=record.fixture_id,
        home_team_id=record.home_team_id,
        away_team_id=record.away_team_id,
        kickoff_utc=record.kickoff_utc,
        as_of_utc=record.as_of_utc,
        predicted_outcome=predicted,
        actual_outcome=actual,
        correct_1x2=predicted == actual,
        p_home=record.p_home,
        p_draw=record.p_draw,
        p_away=record.p_away,
        actual_home_goals=fixture.home_goals,
        actual_away_goals=fixture.away_goals,
        expected_total_goals=expected_total,
        actual_total_goals=actual_total,
        brier=_brier(record.p_home, record.p_draw, record.p_away, actual),
        log_loss=_log_loss(record.p_home, record.p_draw, record.p_away, actual),
        total_goals_error=abs(expected_total - actual_total),
    )


def evaluate_predictions(
    records: list[PredictionRecord],
    fixtures_by_id: dict[str, Fixture],
) -> tuple[EvaluationSummary, list[EvaluatedFixture]]:
    """Compute aggregate metrics from stored ledger rows and finished fixtures.

    Leakage rule: only uses pre-stored predictions; never generates new ones.
    """
    evaluated: list[EvaluatedFixture] = []
    for record in records:
        fixture = fixtures_by_id.get(record.fixture_id)
        if fixture is None:
            continue
        item = evaluate_fixture(record, fixture)
        if item is not None:
            evaluated.append(item)

    if not evaluated:
        return EvaluationSummary(
            n_matches=0,
            accuracy_1x2=0.0,
            brier_score=0.0,
            log_loss=0.0,
            mae_total_goals=0.0,
            model_version=records[0].model_version if records else "",
        ), []

    n = len(evaluated)
    accuracy = sum(1 for item in evaluated if item.correct_1x2) / n
    brier = sum(item.brier for item in evaluated) / n
    logloss = sum(item.log_loss for item in evaluated) / n
    mae_goals = sum(item.total_goals_error for item in evaluated) / n
    calibration = _calibration_bins([(item.p_home, 1.0 if item.actual_outcome == "home_win" else 0.0) for item in evaluated])

    summary = EvaluationSummary(
        n_matches=n,
        accuracy_1x2=accuracy,
        brier_score=brier,
        log_loss=logloss,
        mae_total_goals=mae_goals,
        calibration_bins=calibration,
        model_version=records[0].model_version if records else "",
    )
    return summary, evaluated
