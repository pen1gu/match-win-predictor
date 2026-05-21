from __future__ import annotations

from server.app.tasks.ingest_helpers import (
    IngestCheckpoint,
    current_season_for_league,
    ingest_season_full_details,
    parse_leagues,
    seasons_for_backfill,
)
from server.app.tasks.task import fetch_games_for_league_season_task
from server.config.settings import settings
from server.utils.logger.get_logger import get_logger

logger = get_logger(__name__)


async def historical_backfill_task(
    *,
    leagues: list[str] | None = None,
    start_year: int | None = None,
    include_current_season: bool = False,
) -> dict[str, int]:
    leagues = leagues or parse_leagues()
    start_year = start_year if start_year is not None else settings.backfill_start_year
    checkpoint = IngestCheckpoint.load()

    stats: dict[str, int] = {
        "seasons_processed": 0,
        "schedules_saved": 0,
        "details_saved": 0,
    }

    for league in leagues:
        current = current_season_for_league(league)
        through = None if include_current_season else current
        seasons = seasons_for_backfill(
            league,
            start_year=start_year,
            through_exclusive=through,
        )
        logger.info(
            "historical backfill league=%s seasons=%d range=%s..%s",
            league,
            len(seasons),
            seasons[0] if seasons else "-",
            seasons[-1] if seasons else "-",
        )

        for season in seasons:
            season_cp = checkpoint.get_season(league, season)
            if not season_cp.schedule_done:
                saved = await fetch_games_for_league_season_task(league, season)
                stats["schedules_saved"] += saved
                season_cp.schedule_done = True
                checkpoint.save()
            else:
                logger.info("schedule skip (checkpoint): league=%s season=%s", league, season)

            # Full ingest: teams, players, game_details (not schedule-only).
            details = await ingest_season_full_details(
                league,
                season,
                checkpoint,
                only_finished=False,
            )
            stats["details_saved"] += details
            stats["seasons_processed"] += 1
            logger.info(
                "historical season done: league=%s season=%s details=%d",
                league,
                season,
                details,
            )

    logger.info("historical backfill complete: %s", stats)
    return stats
