"""Tests for the /admin endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from lip.api.main import app
from lip.config import get_settings
from lip.db import get_db


class _FakeSession:
    def scalar(self, _stmt):
        return 0

    def scalars(self, _stmt):
        m = MagicMock()
        m.all.return_value = []
        return m

    def execute(self, _stmt):
        m = MagicMock()
        m.all.return_value = []
        m.scalar_one_or_none.return_value = None
        return m

    def rollback(self) -> None:
        return None


def _client() -> TestClient:
    get_settings.cache_clear()
    app.dependency_overrides[get_db] = lambda: _FakeSession()
    return TestClient(app)


def teardown_function() -> None:
    get_settings.cache_clear()
    app.dependency_overrides.clear()


def test_admin_returns_503_when_token_not_configured(monkeypatch):
    monkeypatch.delenv("LIP_ADMIN_TOKEN", raising=False)
    resp = _client().get("/admin/spiders", headers={"X-Admin-Token": "anything"})
    assert resp.status_code == 503
    assert "LIP_ADMIN_TOKEN" in resp.json()["detail"]


def test_admin_returns_401_on_wrong_token(monkeypatch):
    monkeypatch.setenv("LIP_ADMIN_TOKEN", "expected-secret")
    resp = _client().get("/admin/spiders", headers={"X-Admin-Token": "wrong"})
    assert resp.status_code == 401


def test_admin_returns_401_when_header_missing(monkeypatch):
    monkeypatch.setenv("LIP_ADMIN_TOKEN", "expected-secret")
    resp = _client().get("/admin/spiders")
    assert resp.status_code == 401


def test_admin_lists_spiders_with_correct_token(monkeypatch):
    monkeypatch.setenv("LIP_ADMIN_TOKEN", "expected-secret")
    resp = _client().get("/admin/spiders", headers={"X-Admin-Token": "expected-secret"})
    assert resp.status_code == 200
    assert "job_bank_canada" in resp.json()["spiders"]


def test_scrape_unknown_spider_is_404(monkeypatch):
    monkeypatch.setenv("LIP_ADMIN_TOKEN", "t")
    resp = _client().post(
        "/admin/scrape/does_not_exist",
        headers={"X-Admin-Token": "t"},
    )
    assert resp.status_code == 404
