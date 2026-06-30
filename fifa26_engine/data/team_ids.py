"""Stable team identifiers derived from national team names."""

from __future__ import annotations

import re
import unicodedata

# Canonical aliases so different data sources resolve to one slug.
_TEAM_ALIASES: dict[str, str] = {
    "korea republic": "south-korea",
    "south korea": "south-korea",
    "czechia": "czech-republic",
    "czech republic": "czech-republic",
    "bosnia and herzegovina": "bosnia-herzegovina",
    "bosnia & herzegovina": "bosnia-herzegovina",
    "congo dr": "dr-congo",
    "dr congo": "dr-congo",
    "democratic republic of the congo": "dr-congo",
    "côte d'ivoire": "ivory-coast",
    "cote d'ivoire": "ivory-coast",
    "ivory coast": "ivory-coast",
    "usa": "united-states",
    "united states": "united-states",
    "united states of america": "united-states",
}


def slugify_team_name(name: str) -> str:
    """Return a stable lowercase slug for a national team name."""
    normalized = unicodedata.normalize("NFKD", name.strip())
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_name.lower()
    if lowered in _TEAM_ALIASES:
        return _TEAM_ALIASES[lowered]
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "unknown"
