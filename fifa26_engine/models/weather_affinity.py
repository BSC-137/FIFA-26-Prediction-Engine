"""Team weather and pitch affinity model.

Learns transparent, bucketed performance deltas from historical NT matches under
specific temperature, precipitation, and pitch profiles. Modifiers are small
multiplicative adjustments applied to base xG before structured context adjustments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from fifa26_engine.data.provider import MatchResult, PitchType, WeatherConditions

TempBucket = Literal["cold", "mild", "hot", "unknown"]
RainBucket = Literal["dry", "wet", "unknown"]
AffinityBucket = tuple[TempBucket, RainBucket, PitchType]

MIN_BUCKET_SAMPLES = 5
SHRINKAGE_PRIOR_MATCHES = 8.0
MODIFIER_MIN = 0.94
MODIFIER_MAX = 1.06
DELTA_SCALE = 0.35


@dataclass
class TeamAffinityProfile:
    """Stored affinity deltas for one team."""

    baseline_scored: float = 0.0
    baseline_conceded: float = 0.0
    matches: int = 0
    bucket_deltas: dict[AffinityBucket, dict[str, float]] = field(default_factory=dict)
    bucket_counts: dict[AffinityBucket, int] = field(default_factory=dict)


def _temp_bucket(temperature_c: float | None) -> TempBucket:
    if temperature_c is None:
        return "unknown"
    if temperature_c < 12.0:
        return "cold"
    if temperature_c <= 24.0:
        return "mild"
    return "hot"


def _rain_bucket(precipitation_mm: float | None) -> RainBucket:
    if precipitation_mm is None:
        return "unknown"
    return "wet" if precipitation_mm > 1.0 else "dry"


def _pitch_bucket(pitch_type: PitchType | None) -> PitchType:
    return pitch_type or "unknown"


def _affinity_bucket(
    temperature_c: float | None,
    precipitation_mm: float | None,
    pitch_type: PitchType | None,
) -> AffinityBucket:
    return (_temp_bucket(temperature_c), _rain_bucket(precipitation_mm), _pitch_bucket(pitch_type))


def _clamp_modifier(value: float) -> float:
    return max(MODIFIER_MIN, min(MODIFIER_MAX, value))


def _shrink(delta: float, sample_size: int) -> float:
    weight = sample_size / (sample_size + SHRINKAGE_PRIOR_MATCHES)
    return delta * weight


class WeatherAffinityEngine:
    """Deterministic weather/pitch affinity engine for national teams."""

    def __init__(self) -> None:
        self._profiles: dict[str, TeamAffinityProfile] = {}
        self._is_fitted = False

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    def fit(self, results: list[MatchResult]) -> None:
        """Fit team affinity profiles from historical results."""
        self._profiles = {}
        if not results:
            self._is_fitted = False
            return

        team_matches: dict[str, list[tuple[float, float, AffinityBucket]]] = {}

        for match in results:
            bucket = _affinity_bucket(
                match.temperature_c,
                match.precipitation_mm,
                match.pitch_type,
            )
            for team_id, scored, conceded in (
                (match.home_team_id, float(match.home_goals), float(match.away_goals)),
                (match.away_team_id, float(match.away_goals), float(match.home_goals)),
            ):
                team_matches.setdefault(team_id, []).append((scored, conceded, bucket))

        for team_id, entries in team_matches.items():
            profile = TeamAffinityProfile(matches=len(entries))
            profile.baseline_scored = sum(item[0] for item in entries) / len(entries)
            profile.baseline_conceded = sum(item[1] for item in entries) / len(entries)

            bucket_groups: dict[AffinityBucket, list[tuple[float, float]]] = {}
            for scored, conceded, bucket in entries:
                bucket_groups.setdefault(bucket, []).append((scored, conceded))

            for bucket, values in bucket_groups.items():
                count = len(values)
                profile.bucket_counts[bucket] = count
                avg_scored = sum(item[0] for item in values) / count
                avg_conceded = sum(item[1] for item in values) / count
                scored_delta = (avg_scored - profile.baseline_scored) / max(profile.baseline_scored, 0.5)
                conceded_delta = (profile.baseline_conceded - avg_conceded) / max(profile.baseline_conceded, 0.5)
                if count < MIN_BUCKET_SAMPLES:
                    scored_delta = _shrink(scored_delta, count)
                    conceded_delta = _shrink(conceded_delta, count)
                profile.bucket_deltas[bucket] = {
                    "scored_delta": scored_delta,
                    "conceded_delta": conceded_delta,
                }

            self._profiles[team_id] = profile

        self._is_fitted = True

    @staticmethod
    def from_results(results: list[MatchResult]) -> WeatherAffinityEngine:
        engine = WeatherAffinityEngine()
        engine.fit(results)
        return engine

    def _team_modifier(
        self,
        team_id: str,
        bucket: AffinityBucket,
        labels: list[str],
        side: str,
    ) -> tuple[float, list[str]]:
        profile = self._profiles.get(team_id)
        if profile is None or bucket[0] == "unknown":
            return 1.0, labels

        deltas = profile.bucket_deltas.get(bucket)
        if deltas is None:
            return 1.0, labels

        scored_delta = deltas["scored_delta"]
        conceded_delta = deltas["conceded_delta"]
        attack_factor = 1.0 + _shrink(scored_delta, profile.bucket_counts.get(bucket, 0)) * DELTA_SCALE
        defense_factor = 1.0 + _shrink(conceded_delta, profile.bucket_counts.get(bucket, 0)) * DELTA_SCALE
        combined = (attack_factor + defense_factor) / 2.0
        combined = _clamp_modifier(combined)

        temp, rain, pitch = bucket
        labels.append(f"{side}_affinity:{temp}_{rain}_{pitch}")
        return combined, labels

    def compute_modifiers(
        self,
        home_team_id: str,
        away_team_id: str,
        weather: WeatherConditions | None,
        pitch_type: PitchType,
    ) -> tuple[float, float, list[str]]:
        """Return ``(home_multiplier, away_multiplier, explanation_labels)``."""
        if weather is None or (
            weather.temperature_c is None
            and weather.precipitation_mm is None
            and weather.weather_code is None
        ):
            return 1.0, 1.0, []

        bucket = _affinity_bucket(weather.temperature_c, weather.precipitation_mm, pitch_type)
        labels: list[str] = []
        home_mult, labels = self._team_modifier(home_team_id, bucket, labels, "home")
        away_mult, labels = self._team_modifier(away_team_id, bucket, labels, "away")
        return home_mult, away_mult, labels
