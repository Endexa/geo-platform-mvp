"""Tests for dashboard API endpoints: overview, history, exports."""

import uuid

from app.models.audit import Audit, AuditStatus
from app.models.visibility_score import VisibilityScore
from app.models.page_score import PageScore


def _create_completed_audit(db, user_id, domain="example.com"):
    """Create a completed audit with visibility score and page scores."""
    audit = Audit(
        id=uuid.uuid4(),
        user_id=user_id,
        url=f"https://{domain}",
        domain=domain,
        status=AuditStatus.COMPLETED.value,
        optimization_score=72,
    )
    db.add(audit)
    db.flush()

    vs = VisibilityScore(
        id=uuid.uuid4(),
        audit_id=audit.id,
        overall_score=65,
        per_engine_scores={"chatgpt": 70, "claude": 60, "perplexity": 65, "gemini": 64},
        mention_count=12,
        query_mention_rate=0.8,
        algorithm_version="v2",
    )
    db.add(vs)

    ps = PageScore(
        id=uuid.uuid4(),
        audit_id=audit.id,
        page_url=f"https://{domain}/",
        page_title="Home",
        crawlability_score=80,
        content_structure_score=70,
        structured_data_score=60,
        authority_score=75,
        overall_page_score=72,
        was_scored=True,
    )
    db.add(ps)
    db.flush()

    return audit


# ── Overview ──────────────────────────────────────────────────────────────


def test_dashboard_overview(authenticated_client, db, test_user):
    """GET /dashboard/overview/{id} returns aggregated dashboard data."""
    audit = _create_completed_audit(db, test_user.id)
    resp = authenticated_client.get(f"/api/v1/dashboard/overview/{audit.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["audit_id"] == str(audit.id)
    assert "combined_geo_score" in data
    assert "visibility_score" in data
    assert "optimization_score" in data


def test_dashboard_overview_not_found(authenticated_client):
    """GET /dashboard/overview/{id} returns 404 for unknown audit."""
    fake_id = str(uuid.uuid4())
    resp = authenticated_client.get(f"/api/v1/dashboard/overview/{fake_id}")
    assert resp.status_code == 404


# ── History ───────────────────────────────────────────────────────────────


def test_audit_history(authenticated_client, db, test_user):
    """GET /dashboard/history returns entries for a domain."""
    _create_completed_audit(db, test_user.id, domain="history-test.com")
    resp = authenticated_client.get(
        "/api/v1/dashboard/history", params={"domain": "history-test.com"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "history-test.com"
    assert data["total"] >= 1
    assert len(data["entries"]) >= 1


def test_audit_history_empty(authenticated_client):
    """GET /dashboard/history returns empty for unknown domain."""
    resp = authenticated_client.get(
        "/api/v1/dashboard/history", params={"domain": "nonexistent-domain.xyz"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["entries"] == []


# ── Cross-User Isolation ─────────────────────────────────────────────────


def test_cross_user_isolation(client, db, test_user):
    """User A cannot see User B's dashboard data."""
    audit = _create_completed_audit(db, test_user.id)

    # Register a different user
    email2 = f"other-{uuid.uuid4().hex[:8]}@test.com"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email2, "password": "OtherPass123@"},
    )
    token2 = reg_resp.json()["access_token"]

    resp = client.get(
        f"/api/v1/dashboard/overview/{audit.id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    # Should be 403 (access denied) or 404 (not found — to avoid info leak)
    assert resp.status_code in (403, 404)
