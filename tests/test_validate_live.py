"""Tests for live-data validation toolkit (mocked, no real API)."""

from __future__ import annotations

from pathlib import Path

import pytest

from fifa26_engine.config import ModelConfig, Settings
from fifa26_engine.data.mock_provider import MockFixtureProvider
from fifa26_engine.data.weather_provider import MockWeatherProvider
from fifa26_engine.scripts.validate_live import (
    CheckStatus,
    check_settings,
    run_live_validation,
)


@pytest.mark.asyncio
async def test_validate_live_passes_with_mock_provider(tmp_path: Path) -> None:
    settings = Settings(
        use_mock_data=True,
        weather_provider="mock",
        predictions_db_path=str(tmp_path / "validate.db"),
    )
    report = await run_live_validation(
        settings,
        force_mock=True,
        provider=MockFixtureProvider(),
        weather_provider=MockWeatherProvider(),
    )

    assert report.passed is True
    assert report.overall == "PASS"
    assert report.provider_mode == "mock"
    assert any(check.name == "provider_fixtures" and check.status == CheckStatus.PASS for check in report.checks)
    assert any(check.name == "ledger" and check.status == CheckStatus.PASS for check in report.checks)


@pytest.mark.asyncio
async def test_validate_live_fails_without_api_key_when_live_requested() -> None:
    settings = Settings(api_football_key="", use_mock_data=False)
    report = await run_live_validation(
        settings,
        force_mock=False,
        provider=MockFixtureProvider(),
        weather_provider=MockWeatherProvider(),
        db_path=":memory:",
    )

    settings_check = next(check for check in report.checks if check.name == "settings")
    assert settings_check.status == CheckStatus.FAIL
    assert report.passed is False


def test_check_settings_skips_when_mock_forced() -> None:
    settings = Settings(api_football_key="", use_mock_data=False)
    result = check_settings(settings, force_mock=True)
    assert result.status == CheckStatus.SKIP


@pytest.mark.asyncio
async def test_validate_live_json_report_structure(tmp_path: Path) -> None:
    from fifa26_engine.scripts.validate_live import report_to_dict

    settings = Settings(
        use_mock_data=True,
        predictions_db_path=str(tmp_path / "validate.db"),
    )
    report = await run_live_validation(
        settings,
        force_mock=True,
        provider=MockFixtureProvider(),
        weather_provider=MockWeatherProvider(),
    )
    payload = report_to_dict(report)

    assert payload["overall"] == "PASS"
    assert payload["provider_mode"] == "mock"
    assert isinstance(payload["checks"], list)
    assert all("name" in item and "status" in item for item in payload["checks"])
