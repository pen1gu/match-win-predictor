"""로컬 PostgreSQL DB 생성 → Alembic 마이그레이션 → (선택) ingest."""

from __future__ import annotations

import argparse
import asyncio
import sys
from urllib.parse import urlparse

import psycopg
from alembic import command
from alembic.config import Config

from server.config.settings import settings
from server.utils.logger.get_logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


def _admin_url(database_url_sync: str, admin_db: str = "postgres") -> str:
    parsed = urlparse(database_url_sync.replace("postgresql+psycopg://", "postgresql://"))
    return (
        f"postgresql://{parsed.username}:{parsed.password}"
        f"@{parsed.hostname}:{parsed.port or 5432}/{admin_db}"
    )


def _target_db_name(database_url_sync: str) -> str:
    parsed = urlparse(database_url_sync.replace("postgresql+psycopg://", "postgresql://"))
    db_name = (parsed.path or "").lstrip("/")
    if not db_name:
        raise SystemExit("DATABASE_URL_SYNC에 DB 이름이 없습니다.")
    return db_name


def ensure_database() -> None:
    db_name = _target_db_name(settings.database_url_sync)
    admin_url = _admin_url(settings.database_url_sync)
    with psycopg.connect(admin_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cur.fetchone() is None:
                cur.execute(f'CREATE DATABASE "{db_name}"')
                print(f"created database: {db_name}")
            else:
                print(f"database exists: {db_name}")


def run_migrations() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "001_init")
    print("alembic upgrade 001_init: OK")


async def run_ingest(league: str, season: str, detail_game_id: int | None) -> None:
    from server.app.tasks.task import fetch_game_detail_task, fetch_games_for_league_season_task

    await fetch_games_for_league_season_task(league, season)
    if detail_game_id is not None:
        await fetch_game_detail_task(detail_game_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap local DB and run migrations")
    parser.add_argument("--skip-create-db", action="store_true")
    parser.add_argument("--skip-migrate", action="store_true")
    parser.add_argument("--ingest", action="store_true", help="run schedule ingest after migrate")
    parser.add_argument("--league", default=settings.default_leagues)
    parser.add_argument("--season", default=settings.default_seasons)
    parser.add_argument("--detail-game-id", type=int, help="optional single game detail ingest")
    args = parser.parse_args()

    if not args.skip_create_db:
        ensure_database()
    if not args.skip_migrate:
        run_migrations()
    if args.ingest:
        asyncio.run(run_ingest(args.league, args.season, args.detail_game_id))


if __name__ == "__main__":
    try:
        main()
    except psycopg.OperationalError as exc:
        print("DB connection failed:", exc, file=sys.stderr)
        print(
            "`.env`의 DATABASE_URL_SYNC 사용자/비밀번호를 로컬 PostgreSQL에 맞게 수정하세요.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
