"""Fixture and result data access."""

from fifa26_engine.data.api_football import ApiFootballProvider
from fifa26_engine.data.mock_provider import MockFixtureProvider
from fifa26_engine.data.provider import Fixture, FixtureProvider, MatchResult, Team

__all__ = [
    "ApiFootballProvider",
    "Fixture",
    "FixtureProvider",
    "MatchResult",
    "MockFixtureProvider",
    "Team",
]
