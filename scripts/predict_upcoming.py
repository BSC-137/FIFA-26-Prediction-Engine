"""Run predictions on upcoming WC 2026 fixtures (openfootball data)."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from fifa26_engine.config import ModelConfig, get_settings
from fifa26_engine.config.paths import PROJECT_ROOT
from fifa26_engine.data.stadiums import resolve_stadium
from fifa26_engine.data.weather_provider import create_weather_provider
from fifa26_engine.data.wc2026_store import sync_wc2026_data
from fifa26_engine.services.prediction_service import create_fixture_provider, predict_fixture_markets

UTC = timezone.utc
REPORT_PATH = PROJECT_ROOT / "reports" / "upcoming_predictions.json"


def _weather_dict(breakdown) -> dict | None:
    weather = breakdown.weather_conditions
    if weather is None:
        return None
    return {
        "temperature_c": weather.temperature_c,
        "humidity_pct": weather.humidity_pct,
        "wind_speed_kmh": weather.wind_speed_kmh,
        "precipitation_mm": weather.precipitation_mm,
        "weather_code": weather.weather_code,
        "is_indoor": weather.is_indoor,
    }


def _knockout_dict(breakdown) -> dict | None:
    km = breakdown.knockout_markets
    if km is None:
        return None
    return {
        "regulation_home_win": round(km.regulation_home_win, 4),
        "regulation_draw": round(km.regulation_draw, 4),
        "regulation_away_win": round(km.regulation_away_win, 4),
        "advance_home": round(km.advance_home, 4),
        "advance_away": round(km.advance_away, 4),
    }


def _build_prediction_entry(fixture, breakdown) -> dict:
    markets = breakdown.simulation.markets
    prob_sum = markets["home_win"] + markets["draw"] + markets["away_win"]
    outcomes = {
        "home": markets["home_win"],
        "draw": markets["draw"],
        "away": markets["away_win"],
    }
    model_pick = max(outcomes, key=outcomes.get)  # type: ignore[arg-type]
    stadium = resolve_stadium(fixture)

    return {
        "fixture_id": fixture.fixture_id,
        "match": f"{fixture.home_team_name} vs {fixture.away_team_name}",
        "kickoff_utc": fixture.kickoff_utc.isoformat(),
        "stage": fixture.stage,
        "venue": fixture.venue,
        "venue_city": stadium.city,
        "pitch_type": stadium.pitch_type,
        "model_pick": model_pick,
        "model_pick_prob": round(outcomes[model_pick], 4),
        "probabilities": {
            "home_win": round(markets["home_win"], 4),
            "draw": round(markets["draw"], 4),
            "away_win": round(markets["away_win"], 4),
            "btts_yes": round(markets["btts_yes"], 4),
            "btts_no": round(markets["btts_no"], 4),
            "over_2_5": round(markets["over_2_5"], 4),
            "under_2_5": round(markets["under_2_5"], 4),
        },
        "prob_sum": round(prob_sum, 4),
        "expected_goals": {
            "strength_home": round(breakdown.strength_home_xg, 3),
            "strength_away": round(breakdown.strength_away_xg, 3),
            "base_home": round(breakdown.base_home_xg, 3),
            "base_away": round(breakdown.base_away_xg, 3),
            "adjusted_home": round(breakdown.adjusted_home_xg, 3),
            "adjusted_away": round(breakdown.adjusted_away_xg, 3),
        },
        "weather": _weather_dict(breakdown),
        "adjustments": breakdown.adjustments_applied,
        "warnings": breakdown.warnings or [],
        "diagnostics": {
            "home_attack": round(breakdown.home_attack, 4),
            "away_attack": round(breakdown.away_attack, 4),
            "home_defense": round(breakdown.home_defense, 4),
            "away_defense": round(breakdown.away_defense, 4),
            "n_training_matches": breakdown.n_training_matches,
            "home_wc_matches": breakdown.home_wc_matches,
            "away_wc_matches": breakdown.away_wc_matches,
            "host_boost_applied": breakdown.host_boost_applied,
        },
        "knockout_markets": _knockout_dict(breakdown),
    }


async def main(
    *,
    limit: int | None,
    sync: bool,
    output: Path,
) -> int:
    settings = get_settings()
    if sync:
        data_path = PROJECT_ROOT / settings.wc2026_data_path
        await sync_wc2026_data(
            url=settings.openfootball_wc2026_url,
            data_path=data_path,
        )

    provider = create_fixture_provider(settings)
    if hasattr(provider, "reload"):
        provider.reload()

    weather = create_weather_provider(settings)
    model_config = ModelConfig.from_settings(settings)

    fixtures = await provider.get_fixtures(status="scheduled", limit=500)
    fixtures.sort(key=lambda item: item.kickoff_utc)
    upcoming = fixtures if limit is None else fixtures[:limit]

    if not upcoming:
        print("No scheduled WC 2026 fixtures found.")
        return 1

    print(f"Predicting {len(upcoming)} upcoming WC 2026 fixtures (model {model_config.model_version})...")
    results = []
    for fixture in upcoming:
        breakdown = await predict_fixture_markets(
            fixture,
            provider=provider,
            weather_provider=weather,
            model_config=model_config,
        )
        entry = _build_prediction_entry(fixture, breakdown)
        results.append(entry)
        xg = entry["expected_goals"]
        probs = entry["probabilities"]
        print(
            f"  {fixture.home_team_name} vs {fixture.away_team_name}: "
            f"{entry['model_pick']} ({entry['model_pick_prob']:.0%}) "
            f"xG {xg['adjusted_home']:.2f}-{xg['adjusted_away']:.2f} "
            f"D={probs['draw']:.0%}"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": settings.effective_data_provider,
        "model_version": model_config.model_version,
        "count": len(results),
        "predictions": results,
    }
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved: {output}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Predict upcoming WC 2026 fixtures.")
    parser.add_argument(
        "limit",
        nargs="?",
        type=int,
        default=10,
        help="Number of fixtures to predict (ignored when --all is set).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Predict all scheduled fixtures.",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Sync latest openfootball data before predicting.",
    )
    parser.add_argument(
        "--output",
        default=str(REPORT_PATH),
        help="Output JSON path (default: reports/upcoming_predictions.json).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    fixture_limit = None if args.all else args.limit
    raise SystemExit(
        asyncio.run(
            main(
                limit=fixture_limit,
                sync=args.sync,
                output=Path(args.output),
            ),
        ),
    )
