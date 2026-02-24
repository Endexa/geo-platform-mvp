"""Tests for health and root endpoints (no auth required)."""


def test_health_endpoint(client):
    """GET /health returns 200 with status ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


def test_root_endpoint(client):
    """GET / returns API info."""
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "GEO Platform" in data.get("app", "") or "geo" in str(data).lower()
