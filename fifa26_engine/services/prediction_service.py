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
from fifa26_engine.data.provider import Fixture, FixtureProvider, MatchResult
from fifa26_engine.models.strength import FixturePrediction, TeamStrengthModel
from fifa26_engine.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_TEAM_HISTORY_LIMIT = 30


def create_fixture_provider(settings: Settings | None = None) -> FixtureProvider:
    """Return the appropriate fixture provider based on configuration."""
    resolved = settings or get_settings()
    if resolved.effective_use_mock_data:
        logger.info("Using MockFixtureProvider.")
        return MockFixtureProvider()
    logger.info("Using ApiFootballProvider.")
    return ApiFootballProvider(settings=resolved)


class PredictionService:
    """Coordinates data providers and model layers for predictions."""

    def __init__(
        self,
        provider: FixtureProvider | None = None,
        settings: Settings | None = None,
        team_history_limit: int = DEFAULT_TEAM_HISTORY_LIMIT,
    ) -> None:
        """Initialize the service with an optional provider override."""
        self._settings = settings or get_settings()
        self._provider = provider or create_fixture_provider(self._settings)
        self._team_history_limit = team_history_limit

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

    async def load_recent_results_for_teams(
        self,
        fixture: Fixture,
        limit: int | None = None,
    ) -> list[MatchResult]:
        """Load and deduplicate recent NT results for both teams in a fixture."""
        per_team_limit = limit if limit is not None else self._team_history_limit
        home_results = await self._provider.get_team_results(
            fixture.home_team_id,
            limit=per_team_limit,
        )
        away_results = await self._provider.get_team_results(
            fixture.away_team_id,
            limit=per_team_limit,
        )

        combined: dict[str, MatchResult] = {}
        for result in [*home_results, *away_results]:
            combined[result.match_id] = result

        logger.debug(
            "Loaded %s unique results for fixture %s (home=%s, away=%s)",
            len(combined),
            fixture.fixture_id,
            fixture.home_team_id,
            fixture.away_team_id,
        )
        return list(combined.values())

    async def compute_base_xg(self, fixture: Fixture) -> FixturePrediction:
        """Fit ``TeamStrengthModel`` on recent NT results and return base xG."""
        results = await self.load_recent_results_for_teams(fixture)
        model = TeamStrengthModel.from_results(results)
        prediction = model.predict_fixture(fixture)
        logger.info(
            "Base xG for %s vs %s: %.2f - %.2f (neutral=%s)",
            fixture.home_team_name,
            fixture.away_team_name,
            prediction["home_xg"],
            prediction["away_xg"],
            prediction["is_neutral"],
        )
        return prediction

    async def predict_fixture(self, fixture_id: str) -> MatchPredictionResponse | None:
        """Return a scaffold prediction for a fixture (uniform probabilities for now)."""
        fixture = await self._provider.get_fixture_by_id(fixture_id)
        if fixture is None:
            return None

        # Base xG is computed but not yet wired into outcome probabilities.
        await self.compute_base_xg(fixture)

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
