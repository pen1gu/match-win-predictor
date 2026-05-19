from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/winner_prediction"
    database_echo: bool = False
    database_url_sync: str = "postgresql+psycopg://postgres:postgres@localhost:5432/winner_prediction"

    http_timeout: float = 30.0
    http_max_retries: int = 3
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    sofascore_data_dir: str = ".data/soccerdata"
    default_leagues: str = "ESP-La Liga"
    default_seasons: str = "2024/2025"

    log_level: str = "INFO"
    log_format: str = "text"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000"

    api_v1_prefix: str = "/api/v1"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
