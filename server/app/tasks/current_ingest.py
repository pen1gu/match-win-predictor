from __future__ import annotations

from server.app.tasks.ingest_helpers import (
    current_season_for_league,
    ingest_season_full_details,
    parse_leagues,
)
from server.app.tasks.task import fetch_games_for_league_season_task
from server.utils.logger.get_logger import get_logger

logger = get_logger(__name__)


async def current_season_ingest_task(*, leagues: list[str] | None = None) -> dict[str, int]:
    leagues = leagues or parse_leagues()
    stats: dict[str, int] = {
        "leagues_processed": 0,
        "schedules_saved": 0,
        "details_saved": 0,
    }

    for league in leagues:
        season = current_season_for_league(league)
        logger.info("current ingest start: league=%s season=%s", league, season)

        saved = await fetch_games_for_league_season_task(league, season)
        stats["schedules_saved"] += saved

        details = await ingest_season_full_details(
            league,
            season,
            None,
            only_finished=True,
            only_past_matches=True,
        )
        stats["details_saved"] += details
        stats["leagues_processed"] += 1
        logger.info(
            "current ingest done: league=%s season=%s details=%d",
            league,
            season,
            details,
        )

    logger.info("current season ingest complete: %s", stats)
    return stats
