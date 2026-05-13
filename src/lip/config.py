"""Application configuration, sourced from environment variables.

All settings are namespaced with the ``LIP_`` prefix. See ``.env.example``.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
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

    # Bearer token required to call /admin/* endpoints. When unset the
    # admin routes 503 — there's no implicit-open mode in production.
    admin_token: str | None = None

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        """Accept any common Postgres URL shape and route it through psycopg v3.

        Heroku/Render/Fly's `fly mpg attach` emit `postgres://...`; some tools
        emit `postgresql://...`. SQLAlchemy needs a driver hint
        (`postgresql+psycopg://`) to pick psycopg v3, so we add it here.
        """
        if v.startswith("postgres://"):
            v = "postgresql+psycopg://" + v[len("postgres://") :]
        elif v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://") :]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
