"""Tests for audit API endpoints: create, list, detail, custom queries."""

import uuid

import pytest
from unittest.mock import patch

from app.models.audit import Audit, AuditStatus
from app.models.audit_query import AuditQuery


# ── Helpers ───────────────────────────────────────────────────────────────


def _create_audit(db, user_id, url="https://example.com", status="pending"):
    """Insert an Audit directly in the DB."""
    audit = Audit(
        id=uuid.uuid4(),
        user_id=user_id,
        url=url,
        domain="example.com",
        status=status,
    )
    db.add(audit)
    db.flush()
    return audit


# ── Create Audit ──────────────────────────────────────────────────────────


@patch("app.api.audit.run_crawl_and_generate")
def test_create_audit(mock_celery, authenticated_client):
    """POST /audit/ with a valid URL returns 202."""
    mock_celery.delay.return_value = None
    resp = authenticated_client.post(
        "/api/v1/audit/", json={"url": "https://example.com"}
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["domain"] == "example.com"
    assert data["status"] == "pending"


def test_create_audit_unauthenticated(client):
    """POST /audit/ without auth returns 403."""
    resp = client.post("/api/v1/audit/", json={"url": "https://example.com"})
    assert resp.status_code in (401, 403)


@patch("app.api.audit.run_crawl_and_generate")
def test_create_audit_invalid_url(mock_celery, authenticated_client):
    """POST /audit/ with invalid URL scheme returns 422."""
    mock_celery.delay.return_value = None
    resp = authenticated_client.post(
        "/api/v1/audit/", json={"url": "ftp://example.com"}
    )
    assert resp.status_code == 422


# ── List Audits ───────────────────────────────────────────────────────────


def test_list_audits(authenticated_client, db, test_user):
    """GET /audit/ returns the user's audits."""
    _create_audit(db, test_user.id)
    _create_audit(db, test_user.id, url="https://other.com")

    resp = authenticated_client.get("/api/v1/audit/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2


def test_list_audits_empty(authenticated_client):
    """GET /audit/ returns empty list when user has no audits."""
    resp = authenticated_client.get("/api/v1/audit/")
    assert resp.status_code == 200
    assert resp.json() == []


# ── Get Audit Detail ──────────────────────────────────────────────────────


def test_get_audit_detail(authenticated_client, db, test_user):
    """GET /audit/{id} returns audit with queries and scores."""
    audit = _create_audit(db, test_user.id)
    resp = authenticated_client.get(f"/api/v1/audit/{audit.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(audit.id)
    assert data["domain"] == "example.com"


def test_get_audit_not_found(authenticated_client):
    """GET /audit/{id} returns 404 for nonexistent audit."""
    fake_id = str(uuid.uuid4())
    resp = authenticated_client.get(f"/api/v1/audit/{fake_id}")
    assert resp.status_code == 404


def test_get_audit_other_user(client, db, test_user, test_password):
    """A user cannot access another user's audit."""
    audit = _create_audit(db, test_user.id)

    # Register a second user
    email2 = f"other-{uuid.uuid4().hex[:8]}@test.com"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email2, "password": "OtherPass123@"},
    )
    token2 = reg_resp.json()["access_token"]

    resp = client.get(
        f"/api/v1/audit/{audit.id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 404  # treated as not-found to avoid info leak


# ── Custom Queries ────────────────────────────────────────────────────────


def test_create_custom_query(authenticated_client, db, test_user):
    """POST /audit/{id}/queries creates a custom query with 201."""
    audit = _create_audit(db, test_user.id)
    resp = authenticated_client.post(
        f"/api/v1/audit/{audit.id}/queries",
        json={"query_text": "What is the best SEO tool for beginners?", "category": "general"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_custom"] is True


def test_delete_custom_query(authenticated_client, db, test_user):
    """DELETE /audit/{id}/queries/{qid} removes the query with 204."""
    audit = _create_audit(db, test_user.id)
    query = AuditQuery(
        audit_id=audit.id,
        query_text="Custom query to delete",
        category="general",
        is_custom=True,
        is_editable=True,
    )
    db.add(query)
    db.flush()

    resp = authenticated_client.delete(
        f"/api/v1/audit/{audit.id}/queries/{query.id}"
    )
    assert resp.status_code == 204
