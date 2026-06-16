"""Orchestrates the match prediction flow."""

from __future__ import annotations

from typing import Optional

from fifa26_engine.api.schemas import (
    FixtureResponse,
    MatchPredictionResponse,
    MatchResultSchema,
    PredictionProbabilities,
)
from fifa26_engine.config import Settings, get_settings
from fifa26_engine.data.api_football import ApiFootballProvider
from fifa26_engine.data.mock_provider import MockFixtureProvider
from fifa26_engine.data.provider import FixtureProvider, FixtureRecord
from fifa26_engine.utils.logging import get_logger

logger = get_logger(__name__)


class PredictionService:
    """Coordinates data providers and (future) model layers for predictions."""

    def __init__(
        self,
        provider: Optional[FixtureProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        """Initialize the service with an optional provider override."""
        self._settings = settings or get_settings()
        self._provider = provider or self._default_provider()

    def _default_provider(self) -> FixtureProvider:
        if self._settings.has_api_key:
            logger.info("Using ApiFootballProvider.")
            return ApiFootballProvider(settings=self._settings)
        logger.info("No API key configured; using MockFixtureProvider.")
        return MockFixtureProvider()

    @staticmethod
    def _fixture_to_response(fixture: FixtureRecord) -> FixtureResponse:
        result = None
        if fixture.result is not None:
            result = MatchResultSchema(
                home_goals=fixture.result.home_goals,
                away_goals=fixture.result.away_goals,
                status=fixture.result.status,
            )
        return FixtureResponse(
            fixture_id=fixture.fixture_id,
            competition_id=fixture.competition_id,
            season=fixture.season,
            round=fixture.round,
            kickoff_utc=fixture.kickoff_utc,
            home_team_id=fixture.home_team_id,
            home_team_name=fixture.home_team_name,
            away_team_id=fixture.away_team_id,
            away_team_name=fixture.away_team_name,
            venue=fixture.venue,
            result=result,
        )

    async def list_fixtures(self) -> list[FixtureResponse]:
        """Return fixtures for the configured World Cup competition."""
        fixtures = await self._provider.get_fixtures(
            competition_id=self._settings.world_cup_competition_id,
            season=self._settings.world_cup_season,
        )
        return [self._fixture_to_response(fixture) for fixture in fixtures]

    async def predict_fixture(self, fixture_id: int) -> Optional[MatchPredictionResponse]:
        """Return a scaffold prediction for a fixture (uniform probabilities for now)."""
        fixture = await self._provider.get_fixture(fixture_id)
        if fixture is None:
            return None

        # Placeholder until strength/simulator models are implemented.
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
