"""Run predictions on upcoming WC 2026 fixtures (openfootball data)."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fifa26_engine.config import ModelConfig, get_settings
from fifa26_engine.config.paths import PROJECT_ROOT
from fifa26_engine.data.weather_provider import create_weather_provider
from fifa26_engine.services.prediction_service import create_fixture_provider, predict_fixture_markets

UTC = timezone.utc
REPORT_PATH = PROJECT_ROOT / "reports" / "upcoming_predictions.json"


async def main(limit: int = 10) -> int:
    settings = get_settings()
    provider = create_fixture_provider(settings)
    weather = create_weather_provider(settings)
    model_config = ModelConfig.from_settings(settings)

    fixtures = await provider.get_fixtures(status="scheduled", limit=500)
    fixtures.sort(key=lambda item: item.kickoff_utc)
    upcoming = fixtures[:limit]

    if not upcoming:
        print("No scheduled WC 2026 fixtures found.")
        return 1

    print(f"Predicting {len(upcoming)} upcoming WC 2026 fixtures...")
    results = []
    for fixture in upcoming:
        breakdown = await predict_fixture_markets(
            fixture,
            provider=provider,
            weather_provider=weather,
            model_config=model_config,
        )
        pick = max(
            ("home", breakdown.probabilities.home_win),
            ("draw", breakdown.probabilities.draw),
            ("away", breakdown.probabilities.away_win),
            key=lambda item: item[1],
        )
        results.append(
            {
                "fixture_id": fixture.fixture_id,
                "match": f"{fixture.home_team_name} vs {fixture.away_team_name}",
                "kickoff_utc": fixture.kickoff_utc.isoformat(),
                "stage": fixture.stage,
                "venue": fixture.venue,
                "model_pick": pick[0],
                "model_pick_prob": round(pick[1], 3),
                "home_win": round(breakdown.probabilities.home_win, 3),
                "draw": round(breakdown.probabilities.draw, 3),
                "away_win": round(breakdown.probabilities.away_win, 3),
                "adj_home_xg": round(breakdown.adjusted_home_xg, 2),
                "adj_away_xg": round(breakdown.adjusted_away_xg, 2),
            },
        )
        print(
            f"  {fixture.home_team_name} vs {fixture.away_team_name}: "
            f"{pick[0]} ({pick[1]:.0%}) xG {breakdown.adjusted_home_xg:.2f}-{breakdown.adjusted_away_xg:.2f}"
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": settings.effective_data_provider,
        "count": len(results),
        "predictions": results,
    }
    REPORT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    raise SystemExit(asyncio.run(main(limit=limit)))
