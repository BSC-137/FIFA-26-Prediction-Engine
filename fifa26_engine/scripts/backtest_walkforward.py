"""Walk-forward backtesting with strict temporal leakage guards.

For each finished fixture in chronological order the model is fit only on
``MatchResult`` rows with ``date < kickoff_utc``, context is built from
information available at kickoff, and predictions are compared to actual
outcomes. This script does **not** read or write the prediction ledger.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fifa26_engine.config import Settings, get_settings
from fifa26_engine.data.provider import Fixture, FixtureProvider, MatchResult, WeatherConditions
from fifa26_engine.data.stadiums import enrich_fixture, resolve_stadium
from fifa26_engine.data.weather_provider import WeatherProvider, _bucket_weather_code, create_weather_provider
from fifa26_engine.models.adjustments import AdjustmentEngine, MatchContext
from fifa26_engine.models.evaluation import _argmax_outcome, _brier, _log_loss, _outcome
from fifa26_engine.models.simulator import MatchSimulator
from fifa26_engine.models.strength import TeamStrengthModel
from fifa26_engine.models.temporal import filter_results_before
from fifa26_engine.models.weather_affinity import WeatherAffinityEngine
from fifa26_engine.services.prediction_service import create_fixture_provider

UTC = timezone.utc
MODEL_VERSION = "walkforward-v1"
LIMITATION_NOTE = (
    "Mock weather history may be synthetic; observed kickoff weather is used when "
    "present on a MatchResult, otherwise a weather-provider forecast at kickoff."
)

DEFAULT_MAX_GOALS = 10
DEFAULT_DIXON_COLES_RHO = -0.13
DEFAULT_TEAM_HISTORY_LIMIT = 500


def _is_knockout_stage(stage: str) -> bool:
    lowered = stage.lower()
    keywords = ("round of", "quarter", "semi", "final", "knockout")
    return any(keyword in lowered for keyword in keywords)


def _stage_bucket(stage: str) -> str:
    return "knockout" if _is_knockout_stage(stage) else "group"


def fixture_to_match_result(fixture: Fixture) -> MatchResult | None:
    """Convert a finished fixture to a ``MatchResult`` (scores only, no post-match stats)."""
    if fixture.home_goals is None or fixture.away_goals is None:
        return None
    pitch = fixture.pitch_type if fixture.pitch_type != "unknown" else None
    return MatchResult(
        match_id=fixture.fixture_id,
        date=fixture.kickoff_utc,
        home_team_id=fixture.home_team_id,
        away_team_id=fixture.away_team_id,
        home_goals=fixture.home_goals,
        away_goals=fixture.away_goals,
        is_neutral=False,
        competition=fixture.competition,
        pitch_type=pitch,
    )


def match_result_to_weather(result: MatchResult) -> WeatherConditions | None:
    """Build kickoff weather from observed fields on a historical result."""
    if (
        result.temperature_c is None
        and result.humidity_pct is None
        and result.precipitation_mm is None
    ):
        return None
    return WeatherConditions(
        temperature_c=result.temperature_c,
        humidity_pct=result.humidity_pct,
        wind_speed_kmh=None,
        precipitation_mm=result.precipitation_mm,
        weather_code=_bucket_weather_code(result.temperature_c, result.precipitation_mm),
        fetched_at_utc=result.date,
    )


async def gather_team_results(
    provider: FixtureProvider,
    team_ids: set[str],
    *,
    limit: int = DEFAULT_TEAM_HISTORY_LIMIT,
) -> list[MatchResult]:
    """Load and deduplicate national-team history for all teams in scope."""
    combined: dict[str, MatchResult] = {}
    for team_id in sorted(team_ids):
        batch = await provider.get_team_results(team_id, limit=limit)
        for result in batch:
            combined[result.match_id] = result
    return list(combined.values())


def collect_team_ids(fixtures: list[Fixture], team_results: list[MatchResult]) -> set[str]:
    """Union of team IDs referenced by fixtures and base history."""
    ids: set[str] = set()
    for fixture in fixtures:
        ids.add(fixture.home_team_id)
        ids.add(fixture.away_team_id)
    for result in team_results:
        ids.add(result.home_team_id)
        ids.add(result.away_team_id)
    return ids


def build_training_results(
    base_results: list[MatchResult],
    finished_fixtures: list[Fixture],
    as_of: datetime,
) -> list[MatchResult]:
    """Leakage-safe training pool: all matches strictly before ``as_of``.

    Combines provider team history with tournament fixtures already played
    before the target kickoff. The target fixture (``date == as_of``) and any
    future fixtures are excluded via ``filter_results_before(..., strict=True)``.
    """
    combined: dict[str, MatchResult] = {result.match_id: result for result in base_results}
    for fixture in finished_fixtures:
        converted = fixture_to_match_result(fixture)
        if converted is not None:
            combined[converted.match_id] = converted
    return filter_results_before(list(combined.values()), as_of, strict=True)


def _lookup_observed_weather(
    fixture: Fixture,
    weather_by_match_id: dict[str, MatchResult],
) -> WeatherConditions | None:
    observed = weather_by_match_id.get(fixture.fixture_id)
    if observed is not None:
        return match_result_to_weather(observed)
    return None


async def build_backtest_match_context(
    fixture: Fixture,
    *,
    weather_by_match_id: dict[str, MatchResult],
    weather_provider: WeatherProvider,
) -> MatchContext:
    """Assemble match context using only kickoff-time information."""
    enriched = enrich_fixture(fixture)
    stadium = resolve_stadium(enriched)
    weather = _lookup_observed_weather(enriched, weather_by_match_id)
    if weather is None and stadium.lat is not None and stadium.lon is not None:
        weather = await weather_provider.get_forecast(
            stadium.lat,
            stadium.lon,
            enriched.kickoff_utc,
        )
    return MatchContext(
        is_knockout=_is_knockout_stage(enriched.stage),
        weather=weather,
        pitch_type=stadium.pitch_type,
    )


async def walkforward_predict_fixture(
    fixture: Fixture,
    training_results: list[MatchResult],
    *,
    weather_by_match_id: dict[str, MatchResult],
    weather_provider: WeatherProvider,
    max_goals: int = DEFAULT_MAX_GOALS,
    dixon_coles_rho: float = DEFAULT_DIXON_COLES_RHO,
) -> dict[str, Any]:
    """Predict markets for one fixture using a pre-fit training pool."""
    enriched = enrich_fixture(fixture)
    strength_model = TeamStrengthModel.from_results(training_results)
    xg_prediction = strength_model.predict_fixture(enriched)
    base_home_xg = xg_prediction["home_xg"]
    base_away_xg = xg_prediction["away_xg"]

    affinity_engine = WeatherAffinityEngine.from_results(training_results)
    context = await build_backtest_match_context(
        enriched,
        weather_by_match_id=weather_by_match_id,
        weather_provider=weather_provider,
    )
    weather_modifiers = affinity_engine.compute_modifiers(
        enriched.home_team_id,
        enriched.away_team_id,
        context.weather,
        context.pitch_type,
    )

    adjustment_engine = AdjustmentEngine()
    adjusted_home_xg, adjusted_away_xg, _ = adjustment_engine.apply(
        base_home_xg,
        base_away_xg,
        context,
        weather_modifiers=weather_modifiers,
    )

    simulation = MatchSimulator(
        home_xg=adjusted_home_xg,
        away_xg=adjusted_away_xg,
        max_goals=max_goals,
        dixon_coles_rho=dixon_coles_rho,
    ).simulate()
    markets = simulation.markets

    return {
        "p_home": markets["home_win"],
        "p_draw": markets["draw"],
        "p_away": markets["away_win"],
        "p_over_2_5": markets["over_2_5"],
        "p_btts_yes": markets["btts_yes"],
        "expected_home_goals": adjusted_home_xg,
        "expected_away_goals": adjusted_away_xg,
        "expected_total_goals": adjusted_home_xg + adjusted_away_xg,
    }


@dataclass(frozen=True)
class WalkForwardRow:
    """One walk-forward evaluation step."""

    fixture_id: str
    kickoff_utc: datetime
    stage: str
    stage_bucket: str
    home_team_id: str
    away_team_id: str
    as_of_utc: datetime
    n_training_matches: int
    predicted_outcome: str
    actual_outcome: str
    correct_1x2: bool
    p_home: float
    p_draw: float
    p_away: float
    brier: float
    log_loss: float
    predicted_over_2_5: bool
    actual_over_2_5: bool
    correct_ou_2_5: bool
    predicted_btts_yes: bool
    actual_btts_yes: bool
    correct_btts: bool
    expected_total_goals: float
    actual_total_goals: int
    total_goals_error: float


@dataclass
class WalkForwardMetrics:
    """Aggregate metrics over a set of walk-forward rows."""

    n_matches: int = 0
    accuracy_1x2: float = 0.0
    brier_score: float = 0.0
    log_loss: float = 0.0
    ou_25_hit_rate: float = 0.0
    btts_hit_rate: float = 0.0
    mae_total_goals: float = 0.0


@dataclass
class WalkForwardReport:
    """Full walk-forward backtest output."""

    overall: WalkForwardMetrics
    by_stage: dict[str, WalkForwardMetrics]
    rows: list[WalkForwardRow] = field(default_factory=list)
    computed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    model_version: str = MODEL_VERSION
    limitation_note: str = LIMITATION_NOTE


def _aggregate_metrics(rows: list[WalkForwardRow]) -> WalkForwardMetrics:
    if not rows:
        return WalkForwardMetrics()
    n = len(rows)
    return WalkForwardMetrics(
        n_matches=n,
        accuracy_1x2=sum(1 for row in rows if row.correct_1x2) / n,
        brier_score=sum(row.brier for row in rows) / n,
        log_loss=sum(row.log_loss for row in rows) / n,
        ou_25_hit_rate=sum(1 for row in rows if row.correct_ou_2_5) / n,
        btts_hit_rate=sum(1 for row in rows if row.correct_btts) / n,
        mae_total_goals=sum(row.total_goals_error for row in rows) / n,
    )


def _evaluate_row(
    fixture: Fixture,
    prediction: dict[str, Any],
    *,
    as_of: datetime,
    n_training: int,
) -> WalkForwardRow:
    assert fixture.home_goals is not None and fixture.away_goals is not None
    actual_outcome = _outcome(fixture.home_goals, fixture.away_goals)
    predicted_outcome = _argmax_outcome(
        prediction["p_home"],
        prediction["p_draw"],
        prediction["p_away"],
    )
    actual_total = fixture.home_goals + fixture.away_goals
    predicted_over = prediction["p_over_2_5"] >= 0.5
    actual_over = actual_total > 2.5
    predicted_btts = prediction["p_btts_yes"] >= 0.5
    actual_btts = fixture.home_goals > 0 and fixture.away_goals > 0
    expected_total = prediction["expected_total_goals"]

    return WalkForwardRow(
        fixture_id=fixture.fixture_id,
        kickoff_utc=fixture.kickoff_utc,
        stage=fixture.stage,
        stage_bucket=_stage_bucket(fixture.stage),
        home_team_id=fixture.home_team_id,
        away_team_id=fixture.away_team_id,
        as_of_utc=as_of,
        n_training_matches=n_training,
        predicted_outcome=predicted_outcome,
        actual_outcome=actual_outcome,
        correct_1x2=predicted_outcome == actual_outcome,
        p_home=prediction["p_home"],
        p_draw=prediction["p_draw"],
        p_away=prediction["p_away"],
        brier=_brier(prediction["p_home"], prediction["p_draw"], prediction["p_away"], actual_outcome),
        log_loss=_log_loss(
            prediction["p_home"],
            prediction["p_draw"],
            prediction["p_away"],
            actual_outcome,
        ),
        predicted_over_2_5=predicted_over,
        actual_over_2_5=actual_over,
        correct_ou_2_5=predicted_over == actual_over,
        predicted_btts_yes=predicted_btts,
        actual_btts_yes=actual_btts,
        correct_btts=predicted_btts == actual_btts,
        expected_total_goals=expected_total,
        actual_total_goals=actual_total,
        total_goals_error=abs(expected_total - actual_total),
    )


async def run_walkforward_backtest(
    provider: FixtureProvider,
    *,
    weather_provider: WeatherProvider | None = None,
    max_goals: int = DEFAULT_MAX_GOALS,
    dixon_coles_rho: float = DEFAULT_DIXON_COLES_RHO,
    team_history_limit: int = DEFAULT_TEAM_HISTORY_LIMIT,
) -> WalkForwardReport:
    """Execute chronological walk-forward evaluation over finished fixtures."""
    wp = weather_provider or create_weather_provider()
    all_fixtures = await provider.get_fixtures(limit=10_000)
    finished = sorted(
        [fixture for fixture in all_fixtures if fixture.status == "finished"],
        key=lambda item: item.kickoff_utc,
    )

    provisional_ids = collect_team_ids(all_fixtures, [])
    base_results = await gather_team_results(
        provider,
        provisional_ids,
        limit=team_history_limit,
    )
    team_ids = collect_team_ids(all_fixtures, base_results)
    if team_ids != provisional_ids:
        base_results = await gather_team_results(provider, team_ids, limit=team_history_limit)

    weather_by_match_id = {result.match_id: result for result in base_results}

    rows: list[WalkForwardRow] = []
    for fixture in finished:
        as_of = fixture.kickoff_utc
        training = build_training_results(base_results, finished, as_of)
        prediction = await walkforward_predict_fixture(
            fixture,
            training,
            weather_by_match_id=weather_by_match_id,
            weather_provider=wp,
            max_goals=max_goals,
            dixon_coles_rho=dixon_coles_rho,
        )
        rows.append(
            _evaluate_row(
                fixture,
                prediction,
                as_of=as_of,
                n_training=len(training),
            ),
        )

    by_stage: dict[str, WalkForwardMetrics] = {}
    for bucket in ("group", "knockout"):
        stage_rows = [row for row in rows if row.stage_bucket == bucket]
        if stage_rows:
            by_stage[bucket] = _aggregate_metrics(stage_rows)

    return WalkForwardReport(
        overall=_aggregate_metrics(rows),
        by_stage=by_stage,
        rows=rows,
    )


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def report_to_dict(report: WalkForwardReport) -> dict[str, Any]:
    """Serialize a report for JSON output."""
    return {
        "computed_at": report.computed_at.astimezone(UTC).isoformat(),
        "model_version": report.model_version,
        "limitation_note": report.limitation_note,
        "overall": asdict(report.overall),
        "by_stage": {key: asdict(metrics) for key, metrics in report.by_stage.items()},
        "fixtures": [asdict(row) for row in report.rows],
    }


def render_markdown(report: WalkForwardReport) -> str:
    """Human-readable summary of walk-forward metrics."""
    lines = [
        "# Walk-Forward Backtest Report",
        "",
        f"Computed at: {report.computed_at.astimezone(UTC).isoformat()}",
        f"Model version: {report.model_version}",
        "",
        "> **Limitation:** " + report.limitation_note,
        "",
        "## Overall metrics",
        "",
        f"- Fixtures evaluated: {report.overall.n_matches}",
        f"- 1X2 accuracy: {report.overall.accuracy_1x2:.1%}",
        f"- Brier score: {report.overall.brier_score:.4f}",
        f"- Log loss: {report.overall.log_loss:.4f}",
        f"- O/U 2.5 hit rate: {report.overall.ou_25_hit_rate:.1%}",
        f"- BTTS hit rate: {report.overall.btts_hit_rate:.1%}",
        f"- MAE total goals: {report.overall.mae_total_goals:.3f}",
        "",
    ]

    if report.by_stage:
        lines.append("## Breakdown by stage")
        lines.append("")
        for bucket, metrics in sorted(report.by_stage.items()):
            lines.extend(
                [
                    f"### {bucket.title()}",
                    "",
                    f"- Fixtures: {metrics.n_matches}",
                    f"- 1X2 accuracy: {metrics.accuracy_1x2:.1%}",
                    f"- Brier score: {metrics.brier_score:.4f}",
                    f"- Log loss: {metrics.log_loss:.4f}",
                    f"- O/U 2.5 hit rate: {metrics.ou_25_hit_rate:.1%}",
                    f"- BTTS hit rate: {metrics.btts_hit_rate:.1%}",
                    f"- MAE total goals: {metrics.mae_total_goals:.3f}",
                    "",
                ],
            )

    lines.append("## Per-fixture results")
    lines.append("")
    lines.append("| Fixture | Kickoff | Stage | Pred 1X2 | Actual | O/U 2.5 | BTTS |")
    lines.append("|---------|---------|-------|----------|--------|---------|------|")
    for row in report.rows:
        ou_mark = "Y" if row.correct_ou_2_5 else "N"
        btts_mark = "Y" if row.correct_btts else "N"
        kickoff = row.kickoff_utc.astimezone(UTC).strftime("%Y-%m-%d")
        lines.append(
            f"| {row.fixture_id} | {kickoff} | {row.stage_bucket} | "
            f"{row.predicted_outcome} | {row.actual_outcome} | {ou_mark} | {btts_mark} |",
        )
    lines.append("")
    return "\n".join(lines)


def write_reports(report: WalkForwardReport, output_dir: Path) -> tuple[Path, Path]:
    """Write JSON and Markdown reports to ``output_dir``."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "backtest_walkforward.json"
    md_path = output_dir / "backtest_walkforward.md"

    payload = report_to_dict(report)
    json_path.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


async def _run_async(
    *,
    settings: Settings,
    output_dir: Path,
    use_mock: bool | None,
) -> WalkForwardReport:
    resolved = settings
    if use_mock is not None:
        resolved = settings.model_copy(update={"use_mock_data": use_mock})
    provider = create_fixture_provider(resolved)
    weather_provider = create_weather_provider(resolved)
    report = await run_walkforward_backtest(provider, weather_provider=weather_provider)
    write_reports(report, output_dir)
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run leakage-safe walk-forward backtesting over finished fixtures.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports"),
        help="Directory for backtest_walkforward.json and .md (default: reports)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force MockFixtureProvider regardless of API key configuration",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = _build_parser().parse_args(argv)
    settings = get_settings()
    use_mock = True if args.mock else None
    if use_mock is None and settings.effective_use_mock_data:
        use_mock = True

    report = asyncio.run(
        _run_async(settings=settings, output_dir=args.output_dir, use_mock=use_mock),
    )
    overall = report.overall
    print(
        f"Walk-forward backtest complete: {overall.n_matches} fixtures, "
        f"1X2 accuracy {overall.accuracy_1x2:.1%}, Brier {overall.brier_score:.4f}",
    )
    print(f"Reports written to {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
