"""Application settings loaded from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "trading"
    postgres_password: str = "trading"
    postgres_db: str = "trading"
    database_url: str = "postgresql://trading:trading@localhost:5432/trading"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_url: str = "redis://localhost:6379"

    oanda_api_key: str = ""
    oanda_account_id: str = ""
    oanda_env: str = "practice"

    anthropic_api_key: str = ""
    pushover_token: str = ""
    pushover_user: str = ""
    finnhub_api_key: str = ""


settings = Settings()
