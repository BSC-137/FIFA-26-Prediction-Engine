"""OpenFootball-backed fixture provider for FIFA World Cup 2026 only."""

from __future__ import annotations

from pathlib import Path

from fifa26_engine.config import Settings, get_settings
from fifa26_engine.config.paths import PROJECT_ROOT
from fifa26_engine.data.provider import Fixture, MatchResult
from fifa26_engine.data.wc2026_store import DEFAULT_WC2026_DATA_PATH, WC2026Store, sync_wc2026_data_sync
from fifa26_engine.utils.logging import get_logger

logger = get_logger(__name__)


class OpenFootballProvider:
    """FixtureProvider using the free openfootball/worldcup.json dataset."""

    def __init__(
        self,
        settings: Settings | None = None,
        store: WC2026Store | None = None,
        *,
        auto_sync: bool | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        data_path = Path(self._settings.wc2026_data_path)
        if not data_path.is_absolute():
            data_path = PROJECT_ROOT / data_path
        self._store = store or WC2026Store(data_path=data_path)
        self._auto_sync = (
            self._settings.wc2026_auto_sync if auto_sync is None else auto_sync
        )
        self._ensure_data()

    def _ensure_data(self) -> None:
        if self._store.data_path.is_file():
            self._store.load()
            return
        if not self._auto_sync:
            raise FileNotFoundError(
                f"WC 2026 data missing at {self._store.data_path}. "
                "Set WC2026_AUTO_SYNC=true or run sync_wc2026_data."
            )
        logger.info("WC 2026 data file missing; downloading from openfootball.")
        sync_wc2026_data_sync(
            url=self._settings.openfootball_wc2026_url,
            data_path=self._store.data_path,
        )
        self._store.load()

    def reload(self) -> None:
        """Reload fixtures from disk (after a manual sync)."""
        self._store.load()

    async def sync_from_remote(self) -> None:
        """Download the latest openfootball JSON and reload."""
        from fifa26_engine.data.wc2026_store import sync_wc2026_data

        await sync_wc2026_data(
            url=self._settings.openfootball_wc2026_url,
            data_path=self._store.data_path,
        )
        self.reload()

    def clear_cache(self) -> None:
        """Compatibility hook for refresh service — reloads local data."""
        self.reload()

    async def get_fixtures(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[Fixture]:
        fixtures = self._store.fixtures
        if status is not None:
            fixtures = [fixture for fixture in fixtures if fixture.status == status]
        if limit <= 0:
            return []
        return fixtures[:limit]

    async def get_team_results(
        self,
        team_id: str,
        limit: int = 30,
    ) -> list[MatchResult]:
        results = self._store.team_results.get(team_id, [])
        if limit <= 0:
            return []
        return results[:limit]

    async def get_fixture_by_id(self, fixture_id: str) -> Fixture | None:
        return self._store.get_fixture(fixture_id)
