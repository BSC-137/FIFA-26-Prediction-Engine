"""Live-data validation toolkit for provider and pipeline lock-down."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from fifa26_engine.config import ModelConfig, Settings, get_settings
from fifa26_engine.config.paths import PROJECT_ROOT
from fifa26_engine.data.mock_provider import MockFixtureProvider
from fifa26_engine.data.provider import Fixture, FixtureProvider
from fifa26_engine.data.stadiums import enrich_fixture, resolve_stadium
from fifa26_engine.data.weather_provider import MockWeatherProvider, WeatherProvider, create_weather_provider
from fifa26_engine.services.prediction_service import (
    create_fixture_provider,
    predict_fixture_markets,
)
from fifa26_engine.storage.prediction_store import PredictionStore

UTC = timezone.utc
XG_MIN = 0.15
XG_MAX = 3.8
PROB_SUM_MIN = 0.99
PROB_SUM_MAX = 1.01
LOW_TOTAL_XG_WARN = 0.5
FIXTURE_FETCH_LIMIT = 5


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


@dataclass(frozen=True)
class ValidationCheck:
    """Single validation step result."""

    name: str
    status: CheckStatus
    message: str
    critical: bool = True


@dataclass
class ValidationReport:
    """Aggregate validation output."""

    checks: list[ValidationCheck] = field(default_factory=list)
    computed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    force_mock: bool = False
    provider_mode: str = "unknown"

    @property
    def passed(self) -> bool:
        return all(
            check.status != CheckStatus.FAIL
            for check in self.checks
            if check.critical
        )

    @property
    def overall(self) -> Literal["PASS", "FAIL"]:
        return "PASS" if self.passed else "FAIL"


def _check(
    name: str,
    status: CheckStatus,
    message: str,
    *,
    critical: bool = True,
) -> ValidationCheck:
    return ValidationCheck(name=name, status=status, message=message, critical=critical)


def _print_check(check: ValidationCheck) -> None:
    print(f"[{check.status.value}] {check.name}: {check.message}")


def check_settings(settings: Settings, *, force_mock: bool) -> ValidationCheck:
    """Verify API key is present when live mode is explicitly requested."""
    if force_mock:
        return _check(
            "settings",
            CheckStatus.SKIP,
            "Skipped (--mock forces offline provider).",
            critical=False,
        )
    if settings.use_mock_data is False and not settings.has_api_key:
        return _check(
            "settings",
            CheckStatus.FAIL,
            "USE_MOCK_DATA=false but API_FOOTBALL_KEY is empty. "
            "Paste your key in project_root/.env (see scripts/setup_env.ps1).",
        )
    if settings.effective_use_mock_data:
        return _check(
            "settings",
            CheckStatus.PASS,
            "Mock/offline mode (no live API key required).",
        )
    return _check(
        "settings",
        CheckStatus.PASS,
        "API key configured for live API-Football access.",
    )


async def check_provider_fixtures(
    provider: FixtureProvider,
    settings: Settings,
) -> tuple[ValidationCheck, list[Fixture]]:
    """Fetch fixtures and ensure the provider returns data."""
    fixtures = await provider.get_fixtures(limit=FIXTURE_FETCH_LIMIT)
    if fixtures:
        return (
            _check(
                "provider_fixtures",
                CheckStatus.PASS,
                f"Fetched {len(fixtures)} fixture(s) from provider.",
            ),
            fixtures,
        )

    hint = (
        f"No fixtures returned. Verify WORLD_CUP_LEAGUE_ID={settings.world_cup_league_id} "
        f"and SEASON={settings.season} in .env match API-Football."
    )
    return (
        _check("provider_fixtures", CheckStatus.FAIL, hint),
        [],
    )


def check_fixture_coverage(fixtures: list[Fixture]) -> ValidationCheck:
    """Ensure at least one finished or scheduled fixture exists."""
    finished_or_scheduled = [
        fixture
        for fixture in fixtures
        if fixture.status in ("finished", "scheduled")
    ]
    if finished_or_scheduled:
        counts = {
            status: sum(1 for fixture in fixtures if fixture.status == status)
            for status in ("finished", "scheduled", "live")
        }
        return _check(
            "fixture_coverage",
            CheckStatus.PASS,
            "Found finished/scheduled fixtures "
            f"(finished={counts.get('finished', 0)}, scheduled={counts.get('scheduled', 0)}).",
        )
    return _check(
        "fixture_coverage",
        CheckStatus.FAIL,
        "No finished or scheduled fixtures in provider response.",
    )


async def check_prediction_pipeline(
    fixtures: list[Fixture],
    provider: FixtureProvider,
    *,
    model_config: ModelConfig,
    weather_provider: WeatherProvider,
) -> list[ValidationCheck]:
    """Run prediction pipeline on the first scheduled fixture."""
    scheduled = next((fixture for fixture in fixtures if fixture.status == "scheduled"), None)
    if scheduled is None:
        return [
            _check(
                "prediction_pipeline",
                CheckStatus.SKIP,
                "No scheduled fixture available for prediction smoke test.",
                critical=False,
            ),
        ]

    try:
        breakdown = await predict_fixture_markets(
            scheduled,
            provider,
            model_config=model_config,
            weather_provider=weather_provider,
        )
    except Exception as exc:
        return [
            _check(
                "prediction_pipeline",
                CheckStatus.FAIL,
                f"predict_fixture_markets failed for {scheduled.fixture_id}: {exc}",
            ),
        ]

    markets = breakdown.simulation.markets
    prob_sum = markets["home_win"] + markets["draw"] + markets["away_win"]
    adj_home = breakdown.adjusted_home_xg
    adj_away = breakdown.adjusted_away_xg
    total_xg = adj_home + adj_away
    checks: list[ValidationCheck] = []

    if PROB_SUM_MIN <= prob_sum <= PROB_SUM_MAX:
        checks.append(
            _check(
                "prediction_1x2_probs",
                CheckStatus.PASS,
                f"1X2 probabilities sum to {prob_sum:.4f} for {scheduled.fixture_id}.",
            ),
        )
    else:
        checks.append(
            _check(
                "prediction_1x2_probs",
                CheckStatus.FAIL,
                f"1X2 probabilities sum to {prob_sum:.4f} (expected {PROB_SUM_MIN}–{PROB_SUM_MAX}).",
            ),
        )

    xg_in_range = XG_MIN <= adj_home <= XG_MAX and XG_MIN <= adj_away <= XG_MAX
    if xg_in_range:
        checks.append(
            _check(
                "prediction_xg_bounds",
                CheckStatus.PASS,
                f"Adjusted xG in [{XG_MIN}, {XG_MAX}]: home={adj_home:.3f}, away={adj_away:.3f}.",
            ),
        )
    else:
        checks.append(
            _check(
                "prediction_xg_bounds",
                CheckStatus.FAIL,
                f"Adjusted xG out of range: home={adj_home:.3f}, away={adj_away:.3f}.",
            ),
        )

    if total_xg < LOW_TOTAL_XG_WARN:
        checks.append(
            _check(
                "prediction_total_xg",
                CheckStatus.WARN,
                f"Total adjusted xG is low ({total_xg:.3f} < {LOW_TOTAL_XG_WARN}); "
                "check team history or hyperparameters before tuning.",
                critical=False,
            ),
        )
    else:
        checks.append(
            _check(
                "prediction_total_xg",
                CheckStatus.PASS,
                f"Total adjusted xG={total_xg:.3f}.",
                critical=False,
            ),
        )

    return checks


async def check_weather_forecast(
    fixtures: list[Fixture],
    settings: Settings,
    weather_provider: WeatherProvider,
    *,
    force_mock: bool = False,
) -> ValidationCheck:
    """Fetch kickoff weather when Open-Meteo is configured."""
    if force_mock:
        return _check(
            "weather_forecast",
            CheckStatus.SKIP,
            "Skipped (--mock uses offline weather provider).",
            critical=False,
        )
    if settings.weather_provider != "openmeteo":
        return _check(
            "weather_forecast",
            CheckStatus.SKIP,
            f"Weather provider is '{settings.weather_provider}' (Open-Meteo check skipped).",
            critical=False,
        )

    target = next(
        (fixture for fixture in fixtures if fixture.status == "scheduled"),
        fixtures[0] if fixtures else None,
    )
    if target is None:
        return _check(
            "weather_forecast",
            CheckStatus.SKIP,
            "No fixture available for weather forecast check.",
            critical=False,
        )

    enriched = enrich_fixture(target)
    stadium = resolve_stadium(enriched)
    if stadium.lat is None or stadium.lon is None:
        return _check(
            "weather_forecast",
            CheckStatus.WARN,
            f"No stadium coordinates for venue '{enriched.venue}'; forecast skipped.",
            critical=False,
        )

    try:
        forecast = await weather_provider.get_forecast(
            stadium.lat,
            stadium.lon,
            enriched.kickoff_utc,
        )
    except Exception as exc:
        return _check(
            "weather_forecast",
            CheckStatus.WARN,
            f"Open-Meteo forecast failed: {exc}",
            critical=False,
        )

    if forecast.temperature_c is None and forecast.precipitation_mm is None:
        return _check(
            "weather_forecast",
            CheckStatus.WARN,
            "Open-Meteo returned empty forecast fields.",
            critical=False,
        )

    return _check(
        "weather_forecast",
        CheckStatus.PASS,
        f"Open-Meteo forecast OK for {enriched.fixture_id} "
        f"(temp={forecast.temperature_c}°C, precip={forecast.precipitation_mm}mm).",
        critical=False,
    )


def check_ledger(store_path: str, model_version: str) -> ValidationCheck:
    """Verify prediction ledger database opens and counts rows."""
    try:
        store = PredictionStore(store_path)
        count = store.count_predictions(model_version=model_version)
    except Exception as exc:
        return _check(
            "ledger",
            CheckStatus.FAIL,
            f"PredictionStore failed to open at '{store_path}': {exc}",
        )
    return _check(
        "ledger",
        CheckStatus.PASS,
        f"Prediction ledger OK at '{store_path}' ({count} prediction row(s)).",
    )


async def run_live_validation(
    settings: Settings | None = None,
    *,
    force_mock: bool = False,
    provider: FixtureProvider | None = None,
    weather_provider: WeatherProvider | None = None,
    db_path: str | None = None,
) -> ValidationReport:
    """Execute all live-data validation checks."""
    resolved = settings or get_settings()
    model_config = ModelConfig.from_settings(resolved)
    ledger_path = db_path if db_path is not None else resolved.predictions_db_path

    if force_mock:
        fixture_provider = provider or MockFixtureProvider()
        wp = weather_provider or MockWeatherProvider()
        provider_mode = "mock"
    else:
        fixture_provider = provider or create_fixture_provider(resolved)
        wp = weather_provider or create_weather_provider(resolved)
        provider_mode = resolved.effective_data_provider if not resolved.effective_use_mock_data else "mock"

    report = ValidationReport(force_mock=force_mock, provider_mode=provider_mode)
    report.checks.append(check_settings(resolved, force_mock=force_mock))

    provider_check, fixtures = await check_provider_fixtures(fixture_provider, resolved)
    report.checks.append(provider_check)

    if fixtures:
        report.checks.append(check_fixture_coverage(fixtures))
        report.checks.extend(
            await check_prediction_pipeline(
                fixtures,
                fixture_provider,
                model_config=model_config,
                weather_provider=wp,
            ),
        )
        report.checks.append(
            await check_weather_forecast(fixtures, resolved, wp, force_mock=force_mock),
        )

    report.checks.append(check_ledger(ledger_path, model_config.model_version))

    if hasattr(fixture_provider, "close"):
        await fixture_provider.close()  # type: ignore[operator]
    if hasattr(wp, "close"):
        await wp.close()  # type: ignore[operator]

    return report


def report_to_dict(report: ValidationReport) -> dict[str, Any]:
    """Serialize a validation report for JSON output."""
    return {
        "computed_at": report.computed_at.astimezone(UTC).isoformat(),
        "overall": report.overall,
        "force_mock": report.force_mock,
        "provider_mode": report.provider_mode,
        "checks": [
            {
                "name": check.name,
                "status": check.status.value,
                "message": check.message,
                "critical": check.critical,
            }
            for check in report.checks
        ],
    }


def write_json_report(report: ValidationReport, output_path: Path) -> Path:
    """Write validation report to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report_to_dict(report), indent=2),
        encoding="utf-8",
    )
    return output_path


def print_report(report: ValidationReport) -> None:
    """Print human-readable PASS/FAIL lines."""
    print(f"Live validation - provider_mode={report.provider_mode}")
    print("-" * 60)
    for check in report.checks:
        _print_check(check)
    print("-" * 60)
    print(f"Overall: {report.overall}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate live data provider and prediction pipeline configuration.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force MockFixtureProvider (offline smoke test)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Write reports/validate_live.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "validate_live.json",
        help="JSON output path when --json is set",
    )
    return parser


async def _run_async(*, force_mock: bool, write_json: bool, output_path: Path) -> int:
    report = await run_live_validation(force_mock=force_mock)
    print_report(report)
    if write_json:
        path = write_json_report(report, output_path)
        print(f"Report written to {path.resolve()}")
    return 0 if report.passed else 1


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = _build_parser().parse_args(argv)
    return asyncio.run(
        _run_async(
            force_mock=args.mock,
            write_json=args.json,
            output_path=args.output,
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
