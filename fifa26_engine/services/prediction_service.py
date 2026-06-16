"""Orchestrates the match prediction flow."""

from __future__ import annotations

from fifa26_engine.api.schemas import (
    FixtureResponse,
    MatchPredictionResponse,
    PredictionProbabilities,
)
from fifa26_engine.config import Settings, get_settings
from fifa26_engine.data.api_football import ApiFootballProvider
from fifa26_engine.data.mock_provider import MockFixtureProvider
from fifa26_engine.data.provider import Fixture, FixtureProvider
from fifa26_engine.utils.logging import get_logger

logger = get_logger(__name__)


def create_fixture_provider(settings: Settings | None = None) -> FixtureProvider:
    """Return the appropriate fixture provider based on configuration."""
    resolved = settings or get_settings()
    if resolved.effective_use_mock_data:
        logger.info("Using MockFixtureProvider.")
        return MockFixtureProvider()
    logger.info("Using ApiFootballProvider.")
    return ApiFootballProvider(settings=resolved)


class PredictionService:
    """Coordinates data providers and (future) model layers for predictions."""

    def __init__(
        self,
        provider: FixtureProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize the service with an optional provider override."""
        self._settings = settings or get_settings()
        self._provider = provider or create_fixture_provider(self._settings)

    @staticmethod
    def _fixture_to_response(fixture: Fixture) -> FixtureResponse:
        return FixtureResponse(
            fixture_id=fixture.fixture_id,
            home_team_id=fixture.home_team_id,
            away_team_id=fixture.away_team_id,
            home_team_name=fixture.home_team_name,
            away_team_name=fixture.away_team_name,
            kickoff_utc=fixture.kickoff_utc,
            status=fixture.status,
            competition=fixture.competition,
            stage=fixture.stage,
            venue=fixture.venue,
            home_goals=fixture.home_goals,
            away_goals=fixture.away_goals,
        )

    async def list_fixtures(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[FixtureResponse]:
        """Return World Cup fixtures from the configured provider."""
        fixtures = await self._provider.get_fixtures(status=status, limit=limit)
        return [self._fixture_to_response(fixture) for fixture in fixtures]

    async def predict_fixture(self, fixture_id: str) -> MatchPredictionResponse | None:
        """Return a scaffold prediction for a fixture (uniform probabilities for now)."""
        fixture = await self._provider.get_fixture_by_id(fixture_id)
        if fixture is None:
            return None

        probabilities = PredictionProbabilities(
            home_win=1 / 3,
            draw=1 / 3,
            away_win=1 / 3,
        )
        return MatchPredictionResponse(
            fixture_id=fixture.fixture_id,
            home_team_name=fixture.home_team_name,
            away_team_name=fixture.away_team_name,
            probabilities=probabilities,
        )
