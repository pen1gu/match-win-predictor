# match-win-predictor

Sofascore 기반 축구 승무패 예측 API (Python 3.14, Poetry, FastAPI, SQLModel, Alembic).

## 구조

- `server/` — FastAPI 앱, DB 모델(`games`, `game_id`), ingest, 예측
- `libs/sofascore_httpx/` — Sofascore 공개 API httpx 클라이언트·파서
- `client/web_demo/` — `/api/v1` 호출 데모 UI
- `alembic/` — DB 마이그레이션

**기준점은 항상 Sofascore** (`game_id`, 팀/선수 id).

## 설치

```bash
poetry install
cp .env.example .env
poetry run playwright install chromium
```

## DB 마이그레이션

PostgreSQL 실행 후:

```bash
poetry run alembic upgrade head
```

## API 실행

```bash
poetry run uvicorn server.app.main:app --reload
```

- Swagger: http://127.0.0.1:8000/docs
- 데모 UI: http://127.0.0.1:8000/
- Health: `GET /api/v1/health`
- 최근 경기: `GET /api/v1/games/latest?limit=10&include_outcomes=false`

## 데이터 적재 (태스크)

Python에서 `server.app.tasks.task` 모듈 함수 사용:

- `fetch_games_for_league_season_task(league, season)` — `soccerdata.Sofascore.read_schedule`
- `fetch_game_detail_task(game_id)` — Playwright로 실제 SofaScore 경기 페이지를 열어 상세(팀/라인업/통계) 수집
- `historical_backfill_task()` / `run_ingest.py backfill` — 과거 시즌 전체 백필
- `current_season_ingest_task()` / `run_ingest.py current` — 현재 시즌 지속 갱신

## 검증

```bash
poetry run python -m compileall server client libs
```

Import sweep (DB 없이):

```bash
poetry run python -c "import server.app.main; print('OK')"
```
