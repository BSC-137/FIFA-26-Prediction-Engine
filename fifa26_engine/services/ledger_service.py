"""Prediction ledger orchestration with leakage-safe storage."""

from __future__ import annotations

from datetime import datetime, timezone

from fifa26_engine.api.schemas import MODEL_VERSION
from fifa26_engine.data.provider import Fixture
from fifa26_engine.services.prediction_service import PredictionService
from fifa26_engine.storage.prediction_store import (
    PredictionRecord,
    PredictionStore,
    serialize_json,
)
from fifa26_engine.utils.logging import get_logger

logger = get_logger(__name__)


def _ensure_aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def resolve_ledger_as_of(
    kickoff_utc: datetime,
    as_of_utc: datetime | None = None,
) -> datetime:
    """Resolve modelling cutoff for ledger storage (never after kickoff)."""
    now = _ensure_aware(as_of_utc) if as_of_utc else datetime.now(timezone.utc)
    kickoff = _ensure_aware(kickoff_utc)
    return min(now, kickoff)


class LedgerService:
    """Generate, store, and sync pre-kickoff predictions."""

    def __init__(
        self,
        prediction_service: PredictionService,
        store: PredictionStore,
        model_version: str = MODEL_VERSION,
    ) -> None:
        self._prediction_service = prediction_service
        self._store = store
        self._model_version = model_version

    @property
    def store(self) -> PredictionStore:
        return self._store

    def _breakdown_to_record(
        self,
        fixture: Fixture,
        breakdown,
        as_of_utc: datetime,
    ) -> PredictionRecord:
        markets = breakdown.simulation.markets
        weather = breakdown.weather_conditions
        weather_payload = None
        if weather is not None:
            weather_payload = serialize_json(
                {
                    "temperature_c": weather.temperature_c,
                    "humidity_pct": weather.humidity_pct,
                    "wind_speed_kmh": weather.wind_speed_kmh,
                    "precipitation_mm": weather.precipitation_mm,
                    "weather_code": weather.weather_code,
                    "is_indoor": weather.is_indoor,
                },
            )

        return PredictionRecord(
            fixture_id=fixture.fixture_id,
            generated_at_utc=datetime.now(timezone.utc),
            as_of_utc=as_of_utc,
            kickoff_utc=_ensure_aware(fixture.kickoff_utc),
            home_team_id=fixture.home_team_id,
            away_team_id=fixture.away_team_id,
            base_home_xg=breakdown.base_home_xg,
            base_away_xg=breakdown.base_away_xg,
            adj_home_xg=breakdown.adjusted_home_xg,
            adj_away_xg=breakdown.adjusted_away_xg,
            p_home=markets["home_win"],
            p_draw=markets["draw"],
            p_away=markets["away_win"],
            p_btts_yes=markets["btts_yes"],
            p_over_2_5=markets["over_2_5"],
            top_score_json=serialize_json(markets["top_scores"]),
            weather_json=weather_payload,
            adjustments_json=serialize_json(
                {
                    "adjustments_applied": breakdown.adjustments_applied,
                    "weather_labels": breakdown.weather_labels,
                    "weather_home_modifier": breakdown.weather_home_modifier,
                    "weather_away_modifier": breakdown.weather_away_modifier,
                },
            ),
            model_version=self._model_version,
        )

    async def generate_and_store_prediction(
        self,
        fixture: Fixture,
        as_of_utc: datetime | None = None,
    ) -> PredictionRecord:
        """Generate a leakage-safe prediction and persist it to the ledger.

        Leakage rule: ``as_of_utc`` is clamped to ``<= kickoff_utc`` and passed
        to the modelling pipeline so training uses only ``result.date < as_of_utc``.
        """
        cutoff = resolve_ledger_as_of(fixture.kickoff_utc, as_of_utc)
        breakdown = await self._prediction_service.predict_fixture_markets(
            fixture,
            as_of_utc=cutoff,
        )
        record = self._breakdown_to_record(fixture, breakdown, cutoff)
        saved = self._store.save_prediction(record)
        logger.info(
            "Stored ledger prediction for %s (as_of=%s, kickoff=%s)",
            fixture.fixture_id,
            cutoff.isoformat(),
            fixture.kickoff_utc.isoformat(),
        )
        return saved

    async def sync_ledger(self, fixtures: list[Fixture]) -> int:
        """Sync ledger for upcoming fixtures; never regenerate finished predictions.

        - scheduled/live: store one pre-kickoff prediction if missing
        - finished: skip generation (evaluation reads stored rows only)
        """
        stored = 0
        for fixture in fixtures:
            if fixture.status == "finished":
                # Leakage rule: never refit or regenerate for finished fixtures.
                continue
            if fixture.status not in ("scheduled", "live"):
                continue

            existing = self._store.get_prediction_for_fixture(
                fixture.fixture_id,
                self._model_version,
            )
            if existing is not None:
                continue

            try:
                await self.generate_and_store_prediction(fixture)
                stored += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Ledger sync failed for fixture %s: %s",
                    fixture.fixture_id,
                    exc,
                )
        logger.info("Ledger sync stored %s new predictions", stored)
        return stored
