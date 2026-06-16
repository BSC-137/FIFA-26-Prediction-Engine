"""Fixture and result data access."""

from fifa26_engine.data.api_football import ApiFootballProvider
from fifa26_engine.data.mock_provider import MockFixtureProvider
from fifa26_engine.data.provider import FixtureProvider, FixtureRecord, MatchResult

__all__ = [
    "ApiFootballProvider",
    "FixtureProvider",
    "FixtureRecord",
    "MatchResult",
    "MockFixtureProvider",
]
