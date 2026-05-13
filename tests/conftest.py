"""Shared pytest fixtures."""

import os

# Force test-friendly defaults before any lip.* imports pick up settings.
os.environ.setdefault("LIP_ENV", "test")
os.environ.setdefault("LIP_DATABASE_URL", "postgresql+psycopg://lip:lip@localhost:5432/lip_test")
os.environ.setdefault("LIP_REDIS_URL", "redis://localhost:6379/15")
