from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/match_win_predictor"
    database_echo: bool = False
    database_url_sync: str = "postgresql+psycopg://postgres:postgres@localhost:5432/match_win_predictor"

    http_timeout: float = 30.0
    http_max_retries: int = 3
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    sofascore_data_dir: str = ".data/soccerdata"
    default_leagues: str = "ESP-La Liga"
    default_seasons: str = "2024/2025"

    backfill_leagues: str = (
        "ESP-La Liga,ENG-Premier League,ITA-Serie A,GER-Bundesliga"
    )
    backfill_start_year: int = 2000
    ingest_state_path: str = ".data/ingest_state.json"
    ingest_detail_delay_sec: float = 0.5
    ingest_fetch_player_stats: bool = True

    log_level: str = "INFO"
    log_format: str = "text"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000"

    api_v1_prefix: str = "/api/v1"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def backfill_league_list(self) -> list[str]:
        return [league.strip() for league in self.backfill_leagues.split(",") if league.strip()]


settings = Settings()
