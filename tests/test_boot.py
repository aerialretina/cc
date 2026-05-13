"""Tests for the production boot diagnostic.

These exercise only ``_print_db_diagnostic`` — the rest of ``boot.main``
(``alembic upgrade head`` + ``exec uvicorn``) replaces the process and
isn't unit-testable.
"""

from __future__ import annotations

import lip.boot as boot


def test_unset_url_is_called_out(monkeypatch, capsys):
    monkeypatch.delenv("LIP_DATABASE_URL", raising=False)
    boot._print_db_diagnostic()
    out = capsys.readouterr().out
    assert "LIP_DATABASE_URL is unset" in out


def test_clean_url_is_parsed(monkeypatch, capsys):
    monkeypatch.setenv(
        "LIP_DATABASE_URL",
        "postgresql://u:p@db.example.com:5432/myapp?sslmode=require",
    )
    boot._print_db_diagnostic()
    out = capsys.readouterr().out
    assert "host='db.example.com'" in out
    assert "port=5432" in out
    assert "db='myapp'" in out
    # Password must not appear.
    assert ":p@" not in out


def test_quoted_url_is_flagged(monkeypatch, capsys):
    monkeypatch.setenv(
        "LIP_DATABASE_URL",
        "'postgresql://u:p@db.example.com:5432/myapp'",
    )
    boot._print_db_diagnostic()
    out = capsys.readouterr().out
    assert "looks quoted" in out


def test_whitespace_wrapped_url_is_flagged(monkeypatch, capsys):
    monkeypatch.setenv(
        "LIP_DATABASE_URL",
        "  postgresql://u:p@db.example.com/myapp\n",
    )
    boot._print_db_diagnostic()
    out = capsys.readouterr().out
    assert "looks quoted or whitespace-wrapped" in out
