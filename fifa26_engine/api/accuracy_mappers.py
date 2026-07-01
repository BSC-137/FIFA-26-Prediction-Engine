"""Map accuracy domain models to API schemas."""

from __future__ import annotations

from fifa26_engine.api.schemas import (
    AccuracyFixtureResponse,
    AccuracySummaryResponse,
    CalibrationBinResponse,
)
from fifa26_engine.models.evaluation import EvaluatedFixture, EvaluationSummary
from fifa26_engine.services.accuracy_service import AccuracyReport


def summary_to_response(summary: EvaluationSummary) -> AccuracySummaryResponse:
    return AccuracySummaryResponse(
        n_matches=summary.n_matches,
        accuracy_1x2=summary.accuracy_1x2,
        brier_score=summary.brier_score,
        log_loss=summary.log_loss,
        mae_total_goals=summary.mae_total_goals,
        ou_25_hit_rate=summary.ou_25_hit_rate,
        btts_hit_rate=summary.btts_hit_rate,
        calibration_bins=[
            CalibrationBinResponse(
                bin_start=bin_row.bin_start,
                bin_end=bin_row.bin_end,
                count=bin_row.count,
                mean_predicted=bin_row.mean_predicted,
                actual_rate=bin_row.actual_rate,
            )
            for bin_row in summary.calibration_bins
        ],
        computed_at=summary.computed_at,
        model_version=summary.model_version,
    )


def evaluated_fixture_to_response(item: EvaluatedFixture) -> AccuracyFixtureResponse:
    return AccuracyFixtureResponse(
        fixture_id=item.fixture_id,
        kickoff_utc=item.kickoff_utc,
        as_of_utc=item.as_of_utc,
        predicted_outcome=item.predicted_outcome,
        actual_outcome=item.actual_outcome,
        correct_1x2=item.correct_1x2,
        p_home=item.p_home,
        p_draw=item.p_draw,
        p_away=item.p_away,
        actual_home_goals=item.actual_home_goals,
        actual_away_goals=item.actual_away_goals,
        expected_total_goals=item.expected_total_goals,
        actual_total_goals=item.actual_total_goals,
        brier=item.brier,
        log_loss=item.log_loss,
        total_goals_error=item.total_goals_error,
        predicted_over_2_5=item.predicted_over_2_5,
        actual_over_2_5=item.actual_over_2_5,
        correct_ou_2_5=item.correct_ou_2_5,
        predicted_btts_yes=item.predicted_btts_yes,
        actual_btts_yes=item.actual_btts_yes,
        correct_btts=item.correct_btts,
    )


def report_to_summary_response(report: AccuracyReport) -> AccuracySummaryResponse:
    return summary_to_response(report.summary)
