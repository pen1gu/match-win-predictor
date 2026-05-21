"""DB 적재 태스크 실행 CLI."""

from __future__ import annotations

import argparse
import asyncio

from server.utils.logger.get_logger import configure_logging

configure_logging()

from server.app.tasks.current_ingest import current_season_ingest_task
from server.app.tasks.historical_backfill import historical_backfill_task
from server.app.tasks.task import (
    compute_all_player_ratings_task,
    compute_player_rating_task,
    fetch_game_detail_task,
    fetch_games_for_league_season_task,
)
from server.config.settings import settings


async def _run(args: argparse.Namespace) -> None:
    if args.task == "schedule":
        league = args.league or settings.default_leagues
        season = args.season or settings.default_seasons
        await fetch_games_for_league_season_task(league, season)
        return

    if args.task == "detail":
        if args.game_id is None:
            raise SystemExit("--game-id is required for detail task")
        await fetch_game_detail_task(
            args.game_id,
            league=args.league,
            season=args.season,
        )
        return

    if args.task == "backfill":
        leagues = [args.league] if args.league else None
        await historical_backfill_task(
            leagues=leagues,
            start_year=args.start_year,
            include_current_season=args.include_current_season,
        )
        return

    if args.task == "current":
        leagues = [args.league] if args.league else None
        await current_season_ingest_task(leagues=leagues)
        return

    if args.task == "rating":
        if args.player_id is None:
            raise SystemExit("--player-id is required for rating task")
        await compute_player_rating_task(args.player_id)
        return

    if args.task == "ratings-all":
        await compute_all_player_ratings_task()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run winner-prediction ingest tasks")
    parser.add_argument(
        "task",
        choices=["schedule", "detail", "backfill", "current", "rating", "ratings-all"],
        help=(
            "schedule=league season, detail=game detail, backfill=historical full ingest, "
            "current=current season refresh, rating=single player, ratings-all=all players"
        ),
    )
    parser.add_argument("--league", help="single league override (default: BACKFILL_LEAGUES)")
    parser.add_argument("--season", help=f"default: {settings.default_seasons}")
    parser.add_argument("--start-year", type=int, help=f"backfill from year (default: {settings.backfill_start_year})")
    parser.add_argument(
        "--include-current-season",
        action="store_true",
        help="backfill includes current season (default: excluded)",
    )
    parser.add_argument("--game-id", type=int, help="Sofascore game id for detail task")
    parser.add_argument("--player-id", type=int, help="player id for rating task")
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
