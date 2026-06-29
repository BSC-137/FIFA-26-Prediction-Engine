"""Orchestrates the match prediction flow."""

from __future__ import annotations

from datetime import datetime

from fifa26_engine.api.schemas import (
    FixtureResponse,
    MatchPredictionResponse,
    PredictionProbabilities,
)
from fifa26_engine.config import Settings, get_settings
from fifa26_engine.data.api_football import ApiFootballProvider
from fifa26_engine.data.context_builder import build_match_context
from fifa26_engine.data.mock_provider import MockFixtureProvider
from fifa26_engine.data.provider import Fixture, FixtureProvider, MatchResult
from fifa26_engine.data.stadiums import enrich_fixture
from fifa26_engine.data.weather_provider import WeatherProvider, create_weather_provider
from fifa26_engine.models.adjustments import AdjustmentEngine
from fifa26_engine.models.simulator import MatchSimulator, PredictionBreakdown, SimulationResult
from fifa26_engine.models.strength import FixturePrediction, TeamStrengthModel
from fifa26_engine.models.temporal import filter_results_before, resolve_as_of_utc
from fifa26_engine.models.weather_affinity import WeatherAffinityEngine
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


async def load_recent_results_for_fixture(
    fixture: Fixture,
    provider: FixtureProvider,
    limit: int = DEFAULT_TEAM_HISTORY_LIMIT,
    as_of_utc: datetime | None = None,
) -> list[MatchResult]:
    """Load, deduplicate, and temporally filter NT results for a fixture."""
    home_results = await provider.get_team_results(fixture.home_team_id, limit=limit)
    away_results = await provider.get_team_results(fixture.away_team_id, limit=limit)

    combined: dict[str, MatchResult] = {}
    for result in [*home_results, *away_results]:
        combined[result.match_id] = result

    cutoff = resolve_as_of_utc(fixture.kickoff_utc, fixture.status, as_of_utc)
    return filter_results_before(list(combined.values()), cutoff, strict=True)


async def predict_fixture_markets(
    fixture: Fixture,
    provider: FixtureProvider,
    *,
    team_history_limit: int = DEFAULT_TEAM_HISTORY_LIMIT,
    max_goals: int = 10,
    dixon_coles_rho: float = -0.13,
    as_of_utc: datetime | None = None,
    weather_provider: WeatherProvider | None = None,
) -> PredictionBreakdown:
    """Predict market probabilities with weather and context adjustments.

    Pipeline: base xG → weather affinity → AdjustmentEngine → MatchSimulator.
    """
    enriched = enrich_fixture(fixture)
    results = await load_recent_results_for_fixture(
        enriched,
        provider,
        limit=team_history_limit,
        as_of_utc=as_of_utc,
    )

    strength_model = TeamStrengthModel.from_results(results)
    xg_prediction = strength_model.predict_fixture(enriched)
    base_home_xg = xg_prediction["home_xg"]
    base_away_xg = xg_prediction["away_xg"]

    affinity_engine = WeatherAffinityEngine.from_results(results)
    context = await build_match_context(
        enriched,
        provider=provider,
        weather_provider=weather_provider or create_weather_provider(),
    )
    weather_modifiers = affinity_engine.compute_modifiers(
        enriched.home_team_id,
        enriched.away_team_id,
        context.weather,
        context.pitch_type,
    )

    adjustment_engine = AdjustmentEngine()
    adjusted_home_xg, adjusted_away_xg, adjustment_labels = adjustment_engine.apply(
        base_home_xg,
        base_away_xg,
        context,
        weather_modifiers=weather_modifiers,
    )

    simulator = MatchSimulator(
        home_xg=adjusted_home_xg,
        away_xg=adjusted_away_xg,
        max_goals=max_goals,
        dixon_coles_rho=dixon_coles_rho,
    )
    simulation = simulator.simulate()

    breakdown = PredictionBreakdown(
        simulation=simulation,
        base_home_xg=base_home_xg,
        base_away_xg=base_away_xg,
        adjusted_home_xg=adjusted_home_xg,
        adjusted_away_xg=adjusted_away_xg,
        weather_conditions=context.weather,
        weather_home_modifier=weather_modifiers[0],
        weather_away_modifier=weather_modifiers[1],
        weather_labels=weather_modifiers[2],
        adjustments_applied=adjustment_labels,
    )

    logger.info(
        "Markets for %s vs %s: H %.1f%% D %.1f%% A %.1f%% "
        "(base xG %.2f-%.2f → adj %.2f-%.2f)",
        enriched.home_team_name,
        enriched.away_team_name,
        simulation.markets["home_win"] * 100,
        simulation.markets["draw"] * 100,
        simulation.markets["away_win"] * 100,
        base_home_xg,
        base_away_xg,
        adjusted_home_xg,
        adjusted_away_xg,
    )
    return breakdown


class PredictionService:
    """Coordinates data providers and model layers for predictions."""

    def __init__(
        self,
        provider: FixtureProvider | None = None,
        settings: Settings | None = None,
        team_history_limit: int = DEFAULT_TEAM_HISTORY_LIMIT,
        max_goals: int = 10,
        dixon_coles_rho: float = -0.13,
        weather_provider: WeatherProvider | None = None,
    ) -> None:
        """Initialize the service with an optional provider override."""
        self._settings = settings or get_settings()
        self._provider = provider or create_fixture_provider(self._settings)
        self._team_history_limit = team_history_limit
        self._max_goals = max_goals
        self._dixon_coles_rho = dixon_coles_rho
        self._weather_provider = weather_provider or create_weather_provider(self._settings)

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
        provider: FixtureProvider | None = None,
        as_of_utc: datetime | None = None,
    ) -> list[MatchResult]:
        """Load and temporally filter recent NT results for both teams."""
        per_team_limit = limit if limit is not None else self._team_history_limit
        prov = provider or self._provider
        results = await load_recent_results_for_fixture(
            fixture,
            prov,
            limit=per_team_limit,
            as_of_utc=as_of_utc,
        )
        logger.debug(
            "Loaded %s leakage-safe results for fixture %s",
            len(results),
            fixture.fixture_id,
        )
        return results

    async def compute_base_xg(
        self,
        fixture: Fixture,
        provider: FixtureProvider | None = None,
        as_of_utc: datetime | None = None,
    ) -> FixturePrediction:
        """Fit ``TeamStrengthModel`` on recent NT results and return base xG."""
        results = await self.load_recent_results_for_teams(
            fixture,
            provider=provider,
            as_of_utc=as_of_utc,
        )
        model = TeamStrengthModel.from_results(results)
        prediction = model.predict_fixture(enrich_fixture(fixture))
        logger.info(
            "Base xG for %s vs %s: %.2f - %.2f (neutral=%s)",
            fixture.home_team_name,
            fixture.away_team_name,
            prediction["home_xg"],
            prediction["away_xg"],
            prediction["is_neutral"],
        )
        return prediction

    async def predict_fixture_markets(
        self,
        fixture: Fixture,
        provider: FixtureProvider | None = None,
        as_of_utc: datetime | None = None,
    ) -> PredictionBreakdown:
        """Predict market probabilities using the full adjusted pipeline."""
        return await predict_fixture_markets(
            fixture,
            provider or self._provider,
            team_history_limit=self._team_history_limit,
            max_goals=self._max_goals,
            dixon_coles_rho=self._dixon_coles_rho,
            as_of_utc=as_of_utc,
            weather_provider=self._weather_provider,
        )

    async def predict_fixture(self, fixture_id: str) -> MatchPredictionResponse | None:
        """Return 1X2 prediction probabilities from the simulation pipeline."""
        fixture = await self._provider.get_fixture_by_id(fixture_id)
        if fixture is None:
            return None

        breakdown = await self.predict_fixture_markets(fixture)
        markets = breakdown.simulation.markets

        probabilities = PredictionProbabilities(
            home_win=markets["home_win"],
            draw=markets["draw"],
            away_win=markets["away_win"],
        )
        return MatchPredictionResponse(
            fixture_id=fixture.fixture_id,
            home_team_name=fixture.home_team_name,
            away_team_name=fixture.away_team_name,
            probabilities=probabilities,
            expected_home_goals=breakdown.adjusted_home_xg,
            expected_away_goals=breakdown.adjusted_away_xg,
        )
