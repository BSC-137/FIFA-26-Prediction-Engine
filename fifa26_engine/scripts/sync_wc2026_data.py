"""Sync WC 2026 tournament data from openfootball."""

from __future__ import annotations

import argparse
import asyncio

from fifa26_engine.config import get_settings
from fifa26_engine.config.paths import PROJECT_ROOT
from fifa26_engine.data.wc2026_store import sync_wc2026_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Download latest WC 2026 data from openfootball.")
    parser.add_argument(
        "--url",
        default=None,
        help="Override openfootball JSON URL (default: from settings / openfootball GitHub).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path relative to project root (default: data/wc2026/worldcup.json).",
    )
    args = parser.parse_args()
    settings = get_settings()
    url = args.url or settings.openfootball_wc2026_url
    data_path = PROJECT_ROOT / (args.output or settings.wc2026_data_path)
    path = asyncio.run(sync_wc2026_data(url=url, data_path=data_path))
    print(f"Synced WC 2026 data to {path}")


if __name__ == "__main__":
    main()
