"""Export per-team WC 2026 tournament stats and metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fifa26_engine.config import get_settings
from fifa26_engine.config.paths import PROJECT_ROOT
from fifa26_engine.data.openfootball_provider import OpenFootballProvider
from fifa26_engine.data.team_metrics import compute_all_team_stats
from fifa26_engine.data.wc2026_store import WC2026Store, sync_wc2026_data_sync


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Show WC 2026 stats/metrics for each national team (openfootball data).",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Download latest results from openfootball before computing stats.",
    )
    parser.add_argument(
        "--team",
        default=None,
        help="Filter to one team slug (e.g. mexico, france).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON instead of a table.",
    )
    parser.add_argument(
        "--output",
        default="reports/wc2026_team_stats.json",
        help="Write JSON report to this path (relative to project root).",
    )
    args = parser.parse_args()

    settings = get_settings()
    data_path = PROJECT_ROOT / settings.wc2026_data_path
    if args.sync:
        sync_wc2026_data_sync(url=settings.openfootball_wc2026_url, data_path=data_path)

    store = WC2026Store(data_path=data_path)
    store.load()
    all_stats = compute_all_team_stats(store)

    if args.team:
        filtered = [item for item in all_stats if item.team_id == args.team]
        if not filtered:
            known = ", ".join(item.team_id for item in all_stats[:12])
            raise SystemExit(f"Team '{args.team}' not found. Examples: {known}")
        all_stats = filtered

    payload = {
        "source": "openfootball",
        "competition": "FIFA World Cup 2026",
        "fixture_count": len(store.fixtures),
        "finished_count": sum(1 for fixture in store.fixtures if fixture.status == "finished"),
        "teams": [item.to_dict() for item in all_stats],
    }

    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"WC 2026 team stats ({len(all_stats)} teams with results)")
        print(f"Saved: {output_path}")
        print()
        header = f"{'Team':<22} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'GF':>3} {'GA':>3} {'GD':>4} {'Pts':>4}  Form"
        print(header)
        print("-" * len(header))
        for item in all_stats:
            print(
                f"{item.team_name:<22} {item.played:>3} {item.wins:>3} {item.draws:>3} "
                f"{item.losses:>3} {item.goals_for:>3} {item.goals_against:>3} "
                f"{item.goal_difference:>4} {item.points:>4}  {item.form}"
            )


if __name__ == "__main__":
    main()
