"""Tests for the config layer."""

from __future__ import annotations

from lip.config import Settings


def test_database_url_postgres_scheme_is_rewritten():
    s = Settings(database_url="postgres://u:p@host:5432/db")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"


def test_database_url_postgresql_scheme_is_rewritten():
    s = Settings(database_url="postgresql://u:p@host:5432/db?sslmode=require")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db?sslmode=require"


def test_database_url_already_psycopg_is_untouched():
    s = Settings(database_url="postgresql+psycopg://u:p@host:5432/db")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"
