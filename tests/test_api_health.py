from fastapi.testclient import TestClient

from lip.api.main import app


def test_healthz_returns_ok():
    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
