"""Tests for the plaintext front end.

DB is stubbed via FastAPI's dependency override so the suite stays
hermetic (no Postgres required).
"""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from lip.api.main import app
from lip.db import get_db


class _FakeSession:
    """Minimal Session stand-in that returns 0 for counts and [] for selects."""

    def scalar(self, _stmt):
        return 0

    def scalars(self, _stmt):
        mock = MagicMock()
        mock.all.return_value = []
        return mock

    def execute(self, _stmt):
        mock = MagicMock()
        mock.all.return_value = []
        return mock

    def rollback(self) -> None:
        return None


def _client() -> TestClient:
    app.dependency_overrides[get_db] = lambda: _FakeSession()
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_index_renders_with_empty_db():
    resp = _client().get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "Labor Intelligence Platform" in resp.text
    assert "canonical postings" in resp.text
    assert "job_bank_canada" in resp.text


def test_postings_view_shows_empty_state():
    resp = _client().get("/ui/postings")
    assert resp.status_code == 200
    assert "No canonical postings yet" in resp.text


def test_organizations_view_shows_empty_state():
    resp = _client().get("/ui/organizations")
    assert resp.status_code == 200
    assert "No organizations yet" in resp.text


def test_compensation_view_shows_empty_state():
    resp = _client().get("/ui/compensation")
    assert resp.status_code == 200
    assert "No compensation records yet" in resp.text


def test_projects_view_shows_empty_state():
    resp = _client().get("/ui/projects")
    assert resp.status_code == 200
    assert "No projects yet" in resp.text


def test_nav_present_on_every_page():
    client = _client()
    for path in ("/", "/ui/postings", "/ui/organizations", "/ui/compensation", "/ui/projects"):
        resp = client.get(path)
        assert resp.status_code == 200, path
        for href in ("/ui/postings", "/ui/organizations", "/ui/compensation", "/ui/projects"):
            assert href in resp.text, f"{href} missing in {path}"
