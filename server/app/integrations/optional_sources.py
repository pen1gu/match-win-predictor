"""Optional enrichment sources — always Sofascore spine first.

FBref/Understat/etc. may attach extra columns to an existing `game_id` row when
fuzzy matching succeeds. Conflicts resolve in favor of Sofascore.
"""

from __future__ import annotations

from typing import Any


def enrich_game_from_optional_sources(game_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Placeholder for future optional-source enrichment."""
    return payload
