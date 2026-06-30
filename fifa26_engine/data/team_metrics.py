"""Per-team tournament statistics derived from WC 2026 match results."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from fifa26_engine.data.provider import Fixture, MatchResult
from fifa26_engine.data.wc2026_store import WC2026Store


@dataclass(frozen=True)
class TeamTournamentStats:
    """Aggregated WC 2026 stats for one national team."""

    team_id: str
    team_name: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    avg_goals_for: float
    avg_goals_against: float
    clean_sheets: int
    form: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _team_name_from_fixtures(team_id: str, fixtures: list[Fixture]) -> str:
    for fixture in fixtures:
        if fixture.home_team_id == team_id:
            return fixture.home_team_name
        if fixture.away_team_id == team_id:
            return fixture.away_team_name
    return team_id


def _outcome_for_team(result: MatchResult, team_id: str) -> tuple[int, int, str]:
    """Return (goals_for, goals_against, W/D/L) for the given team."""
    if result.home_team_id == team_id:
        goals_for, goals_against = result.home_goals, result.away_goals
    else:
        goals_for, goals_against = result.away_goals, result.home_goals

    if goals_for > goals_against:
        return goals_for, goals_against, "W"
    if goals_for < goals_against:
        return goals_for, goals_against, "L"
    return goals_for, goals_against, "D"


def compute_team_stats(
    team_id: str,
    results: list[MatchResult],
    *,
    team_name: str | None = None,
    form_length: int = 5,
) -> TeamTournamentStats:
    """Compute tournament stats from finished WC 2026 matches for one team."""
    wins = draws = losses = 0
    goals_for = goals_against = 0
    clean_sheets = 0
    form_chars: list[str] = []

    sorted_results = sorted(results, key=lambda item: item.date)
    for result in sorted_results:
        gf, ga, outcome = _outcome_for_team(result, team_id)
        goals_for += gf
        goals_against += ga
        if outcome == "W":
            wins += 1
        elif outcome == "D":
            draws += 1
        else:
            losses += 1
        if ga == 0:
            clean_sheets += 1
        form_chars.append(outcome)

    played = wins + draws + losses
    form = "".join(form_chars[-form_length:]) if form_chars else ""
    avg_for = round(goals_for / played, 2) if played else 0.0
    avg_against = round(goals_against / played, 2) if played else 0.0

    return TeamTournamentStats(
        team_id=team_id,
        team_name=team_name or team_id,
        played=played,
        wins=wins,
        draws=draws,
        losses=losses,
        goals_for=goals_for,
        goals_against=goals_against,
        goal_difference=goals_for - goals_against,
        points=wins * 3 + draws,
        avg_goals_for=avg_for,
        avg_goals_against=avg_against,
        clean_sheets=clean_sheets,
        form=form,
    )


def compute_all_team_stats(store: WC2026Store) -> list[TeamTournamentStats]:
    """Return stats for every team that has played at least one WC 2026 match."""
    store.ensure_loaded()
    fixtures = store.fixtures
    stats: list[TeamTournamentStats] = []

    for team_id, results in store.team_results.items():
        if not results:
            continue
        name = _team_name_from_fixtures(team_id, fixtures)
        stats.append(compute_team_stats(team_id, results, team_name=name))

    stats.sort(key=lambda item: (-item.points, -item.goal_difference, -item.goals_for, item.team_name))
    return stats
