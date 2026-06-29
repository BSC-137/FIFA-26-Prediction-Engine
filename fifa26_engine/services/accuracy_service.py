"""Accuracy evaluation orchestration from the prediction ledger."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fifa26_engine.data.provider import Fixture
from fifa26_engine.models.evaluation import EvaluatedFixture, EvaluationSummary, evaluate_predictions
from fifa26_engine.services.ledger_service import LedgerService
from fifa26_engine.services.prediction_service import PredictionService
from fifa26_engine.storage.prediction_store import PredictionStore


@dataclass
class AccuracyReport:
    """Cached accuracy report with per-fixture detail."""

    summary: EvaluationSummary
    fixtures: list[EvaluatedFixture]
    computed_at: datetime


class AccuracyService:
    """Recompute metrics from stored ledger rows (never refits models)."""

    def __init__(
        self,
        ledger_service: LedgerService,
        prediction_service: PredictionService,
    ) -> None:
        self._ledger = ledger_service
        self._prediction_service = prediction_service
        self._cached_report: AccuracyReport | None = None

    @property
    def cached_report(self) -> AccuracyReport | None:
        return self._cached_report

    async def recompute(self, fixtures: list[Fixture] | None = None) -> AccuracyReport:
        """Recompute accuracy metrics from stored predictions and finished results."""
        if fixtures is None:
            fixtures = await self._prediction_service.provider.get_fixtures(limit=500)

        fixtures_by_id = {fixture.fixture_id: fixture for fixture in fixtures}
        records = self._ledger.store.list_predictions(limit=500)
        summary, evaluated = evaluate_predictions(records, fixtures_by_id)

        report = AccuracyReport(
            summary=summary,
            fixtures=evaluated,
            computed_at=datetime.now(timezone.utc),
        )
        self._cached_report = report
        return report

    async def get_fixture_evaluations(self, limit: int = 50) -> list[EvaluatedFixture]:
        """Return per-fixture evaluations, recomputing if cache is empty."""
        if self._cached_report is None:
            await self.recompute()
        assert self._cached_report is not None
        return self._cached_report.fixtures[:limit]

    async def get_summary(self) -> EvaluationSummary:
        if self._cached_report is None:
            await self.recompute()
        assert self._cached_report is not None
        return self._cached_report.summary
