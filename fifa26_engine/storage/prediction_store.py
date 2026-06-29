"""SQLite persistence for pre-kickoff prediction ledger entries.

Leakage policy
--------------
* ``as_of_utc`` must be <= ``kickoff_utc`` for every stored row.
* One canonical row per ``(fixture_id, model_version)`` — never overwrite with
  post-kickoff data for finished-match evaluation.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from fifa26_engine.api.schemas import MODEL_VERSION

_SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fixture_id TEXT NOT NULL,
    generated_at_utc TEXT NOT NULL,
    as_of_utc TEXT NOT NULL,
    kickoff_utc TEXT NOT NULL,
    home_team_id TEXT NOT NULL,
    away_team_id TEXT NOT NULL,
    base_home_xg REAL NOT NULL,
    base_away_xg REAL NOT NULL,
    adj_home_xg REAL NOT NULL,
    adj_away_xg REAL NOT NULL,
    p_home REAL NOT NULL,
    p_draw REAL NOT NULL,
    p_away REAL NOT NULL,
    top_score_json TEXT NOT NULL,
    weather_json TEXT,
    adjustments_json TEXT NOT NULL,
    model_version TEXT NOT NULL,
    UNIQUE(fixture_id, model_version)
);
CREATE INDEX IF NOT EXISTS idx_predictions_kickoff ON predictions(kickoff_utc);
"""


@dataclass(frozen=True)
class PredictionRecord:
    """A persisted pre-kickoff model prediction."""

    fixture_id: str
    generated_at_utc: datetime
    as_of_utc: datetime
    kickoff_utc: datetime
    home_team_id: str
    away_team_id: str
    base_home_xg: float
    base_away_xg: float
    adj_home_xg: float
    adj_away_xg: float
    p_home: float
    p_draw: float
    p_away: float
    top_score_json: str
    weather_json: str | None
    adjustments_json: str
    model_version: str = MODEL_VERSION
    id: int | None = None


def _ensure_aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _to_iso(moment: datetime) -> str:
    return _ensure_aware(moment).isoformat()


def _from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _validate_leakage_safe(record: PredictionRecord) -> None:
    """Reject records that would leak post-kickoff information."""
    if _ensure_aware(record.as_of_utc) > _ensure_aware(record.kickoff_utc):
        raise ValueError(
            f"as_of_utc ({record.as_of_utc}) must be <= kickoff_utc ({record.kickoff_utc})",
        )


def _row_to_record(row: sqlite3.Row) -> PredictionRecord:
    return PredictionRecord(
        id=row["id"],
        fixture_id=row["fixture_id"],
        generated_at_utc=_from_iso(row["generated_at_utc"]),
        as_of_utc=_from_iso(row["as_of_utc"]),
        kickoff_utc=_from_iso(row["kickoff_utc"]),
        home_team_id=row["home_team_id"],
        away_team_id=row["away_team_id"],
        base_home_xg=row["base_home_xg"],
        base_away_xg=row["base_away_xg"],
        adj_home_xg=row["adj_home_xg"],
        adj_away_xg=row["adj_away_xg"],
        p_home=row["p_home"],
        p_draw=row["p_draw"],
        p_away=row["p_away"],
        top_score_json=row["top_score_json"],
        weather_json=row["weather_json"],
        adjustments_json=row["adjustments_json"],
        model_version=row["model_version"],
    )


class PredictionStore:
    """Thread-safe SQLite store for prediction ledger rows."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._lock = Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def save_prediction(self, record: PredictionRecord) -> PredictionRecord:
        """Insert the canonical pre-kickoff row for a fixture (no overwrite)."""
        _validate_leakage_safe(record)
        existing = self.get_prediction_for_fixture(record.fixture_id, record.model_version)
        if existing is not None:
            return existing

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO predictions (
                    fixture_id, generated_at_utc, as_of_utc, kickoff_utc,
                    home_team_id, away_team_id,
                    base_home_xg, base_away_xg, adj_home_xg, adj_away_xg,
                    p_home, p_draw, p_away,
                    top_score_json, weather_json, adjustments_json, model_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.fixture_id,
                    _to_iso(record.generated_at_utc),
                    _to_iso(record.as_of_utc),
                    _to_iso(record.kickoff_utc),
                    record.home_team_id,
                    record.away_team_id,
                    record.base_home_xg,
                    record.base_away_xg,
                    record.adj_home_xg,
                    record.adj_away_xg,
                    record.p_home,
                    record.p_draw,
                    record.p_away,
                    record.top_score_json,
                    record.weather_json,
                    record.adjustments_json,
                    record.model_version,
                ),
            )
            conn.commit()
            row = conn.execute(
                """
                SELECT * FROM predictions
                WHERE fixture_id = ? AND model_version = ?
                """,
                (record.fixture_id, record.model_version),
            ).fetchone()
        if row is None:
            raise RuntimeError(f"Failed to persist prediction for {record.fixture_id}")
        return _row_to_record(row)

    def get_prediction_for_fixture(
        self,
        fixture_id: str,
        model_version: str = MODEL_VERSION,
    ) -> PredictionRecord | None:
        """Return the stored canonical prediction for a fixture."""
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM predictions
                WHERE fixture_id = ? AND model_version = ?
                """,
                (fixture_id, model_version),
            ).fetchone()
        return _row_to_record(row) if row else None

    def list_predictions(
        self,
        limit: int = 100,
        model_version: str = MODEL_VERSION,
    ) -> list[PredictionRecord]:
        """List stored predictions ordered by kickoff descending."""
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM predictions
                WHERE model_version = ?
                ORDER BY kickoff_utc DESC
                LIMIT ?
                """,
                (model_version, limit),
            ).fetchall()
        return [_row_to_record(row) for row in rows]

    def count_predictions(self, model_version: str = MODEL_VERSION) -> int:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM predictions WHERE model_version = ?",
                (model_version,),
            ).fetchone()
        return int(row["c"]) if row else 0


def serialize_json(value: Any) -> str:
    """JSON helper for ledger persistence."""
    return json.dumps(value, default=str)
