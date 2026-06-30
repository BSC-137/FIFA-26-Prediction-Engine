"""Grid-search hyperparameter tuning via walk-forward backtesting.

Searches only over ``dixon_coles_rho``, ``shrinkage_prior_matches``, and
``team_history_limit``. Does not tune adjustment-rule constants.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fifa26_engine.config import ModelConfig, Settings, get_settings
from fifa26_engine.data.weather_provider import create_weather_provider
from fifa26_engine.scripts.backtest_walkforward import run_walkforward_backtest
from fifa26_engine.services.prediction_service import create_fixture_provider

UTC = timezone.utc

RHO_GRID = [-0.18, -0.13, -0.08, -0.05]
SHRINKAGE_GRID = [4.0, 6.0, 8.0, 10.0, 12.0]
HISTORY_GRID = [20, 30, 40, 50]


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


async def run_grid_search(
    base_config: ModelConfig,
    *,
    use_mock: bool = True,
) -> dict[str, Any]:
    """Evaluate the grid and return results with the best configuration by log loss."""
    settings = get_settings()
    if use_mock:
        settings = settings.model_copy(update={"use_mock_data": True})

    provider = create_fixture_provider(settings)
    weather_provider = create_weather_provider(settings)

    trials: list[dict[str, Any]] = []
    best_log_loss = float("inf")
    best_params: dict[str, float | int] | None = None
    best_metrics: dict[str, Any] | None = None

    for rho in RHO_GRID:
        for shrinkage in SHRINKAGE_GRID:
            for history_limit in HISTORY_GRID:
                trial_config = base_config.with_overrides(
                    dixon_coles_rho=rho,
                    shrinkage_prior_matches=shrinkage,
                    team_history_limit=history_limit,
                )
                report = await run_walkforward_backtest(
                    provider,
                    model_config=trial_config,
                    weather_provider=weather_provider,
                )
                metrics = asdict(report.overall)
                trial = {
                    "dixon_coles_rho": rho,
                    "shrinkage_prior_matches": shrinkage,
                    "team_history_limit": history_limit,
                    "metrics": metrics,
                }
                trials.append(trial)

                log_loss = report.overall.log_loss
                if report.overall.n_matches > 0 and log_loss < best_log_loss:
                    best_log_loss = log_loss
                    best_params = {
                        "dixon_coles_rho": rho,
                        "shrinkage_prior_matches": shrinkage,
                        "team_history_limit": history_limit,
                    }
                    best_metrics = metrics

    return {
        "computed_at": datetime.now(UTC).isoformat(),
        "grid": {
            "dixon_coles_rho": RHO_GRID,
            "shrinkage_prior_matches": SHRINKAGE_GRID,
            "team_history_limit": HISTORY_GRID,
        },
        "n_trials": len(trials),
        "best_by_log_loss": {
            "params": best_params,
            "metrics": best_metrics,
        },
        "trials": trials,
    }


def write_tuning_results(payload: dict[str, Any], output_path: Path) -> Path:
    """Persist tuning output to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, default=_json_default),
        encoding="utf-8",
    )
    return output_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Grid-search model hyperparameters using walk-forward backtesting.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/tuning_results.json"),
        help="Output JSON path (default: reports/tuning_results.json)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force mock provider for offline tuning",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = _build_parser().parse_args(argv)
    settings = get_settings()
    base_config = ModelConfig.from_settings(settings)
    use_mock = args.mock or settings.effective_use_mock_data

    payload = asyncio.run(run_grid_search(base_config, use_mock=use_mock))
    write_tuning_results(payload, args.output)

    best = payload["best_by_log_loss"]
    if best["params"]:
        print(
            "Best params by log loss:",
            best["params"],
            f"(log_loss={best['metrics']['log_loss']:.4f})",
        )
    else:
        print("No finished fixtures available for tuning.")
    print(f"Results written to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
