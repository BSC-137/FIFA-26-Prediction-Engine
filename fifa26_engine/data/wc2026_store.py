"""Local cache and sync for World Cup 2026 openfootball data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from fifa26_engine.config.paths import PROJECT_ROOT
from fifa26_engine.data.openfootball_loader import load_openfootball_payload
from fifa26_engine.data.provider import Fixture, MatchResult
from fifa26_engine.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_WC2026_DATA_PATH = PROJECT_ROOT / "data" / "wc2026" / "worldcup.json"
DEFAULT_OPENFOOTBALL_URL = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
)


class WC2026Store:
    """In-memory view of the WC 2026 tournament backed by a local JSON file."""

    def __init__(self, data_path: Path | None = None) -> None:
        self._data_path = data_path or DEFAULT_WC2026_DATA_PATH
        self._fixtures: list[Fixture] = []
        self._team_results: dict[str, list[MatchResult]] = {}
        self._by_id: dict[str, Fixture] = {}
        self._loaded = False

    @property
    def data_path(self) -> Path:
        return self._data_path

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        """Load tournament data from the local JSON file."""
        if not self._data_path.is_file():
            raise FileNotFoundError(
                f"WC 2026 data file not found at {self._data_path}. "
                "Run: python -m fifa26_engine.scripts.sync_wc2026_data"
            )
        payload = json.loads(self._data_path.read_text(encoding="utf-8"))
        self._apply_payload(payload)

    def _apply_payload(self, payload: dict[str, Any]) -> None:
        fixtures, team_results = load_openfootball_payload(payload)
        self._fixtures = fixtures
        self._team_results = team_results
        self._by_id = {fixture.fixture_id: fixture for fixture in fixtures}
        self._loaded = True
        finished = sum(1 for fixture in fixtures if fixture.status == "finished")
        logger.info(
            "Loaded WC 2026 data: fixtures=%s finished=%s teams=%s path=%s",
            len(fixtures),
            finished,
            len(team_results),
            self._data_path,
        )

    def ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    @property
    def fixtures(self) -> list[Fixture]:
        self.ensure_loaded()
        return self._fixtures

    @property
    def team_results(self) -> dict[str, list[MatchResult]]:
        self.ensure_loaded()
        return self._team_results

    def get_fixture(self, fixture_id: str) -> Fixture | None:
        self.ensure_loaded()
        return self._by_id.get(fixture_id)

    def team_ids(self) -> list[str]:
        self.ensure_loaded()
        return sorted(self._team_results.keys())


async def sync_wc2026_data(
    *,
    url: str = DEFAULT_OPENFOOTBALL_URL,
    data_path: Path | None = None,
    client: httpx.AsyncClient | None = None,
) -> Path:
    """Download the latest openfootball WC 2026 JSON and save it locally."""
    target = data_path or DEFAULT_WC2026_DATA_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=60.0)
    try:
        logger.info("Syncing WC 2026 data from %s", url)
        response = await http.get(url)
        response.raise_for_status()
        payload = response.json()
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        logger.info("Saved WC 2026 data to %s (%s matches)", target, len(payload.get("matches", [])))
        return target
    finally:
        if owns_client:
            await http.aclose()


def sync_wc2026_data_sync(
    *,
    url: str = DEFAULT_OPENFOOTBALL_URL,
    data_path: Path | None = None,
) -> Path:
    """Synchronous wrapper for ``sync_wc2026_data``."""
    import asyncio

    return asyncio.run(sync_wc2026_data(url=url, data_path=data_path))
