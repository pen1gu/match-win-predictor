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
- `fetch_game_detail_task(game_id)` — `libs/sofascore_httpx` 상세

## 검증

```bash
poetry run python -m compileall server client libs
```

Import sweep (DB 없이):

```bash
poetry run python -c "import server.app.main; print('OK')"
```
