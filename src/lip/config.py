"""Application configuration, sourced from environment variables.

All settings are namespaced with the ``LIP_`` prefix. See ``.env.example``.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LIP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["development", "test", "staging", "production"] = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://lip:lip@localhost:5432/lip"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint: str | None = None
    s3_bucket: str = "lip-raw"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_region: str = "us-east-1"

    scrape_user_agent: str = "LIPBot/0.1"
    proxy_url: str | None = None

    bls_api_key: str | None = None
    statcan_api_key: str | None = None
    job_bank_user_id: str | None = None

    geocoder: str | None = None
    geocoder_api_key: str | None = None

    semantic_dedup_threshold: float = Field(default=0.92, ge=0.0, le=1.0)
    cross_source_dedup_window_days: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
