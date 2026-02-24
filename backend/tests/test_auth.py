"""Tests for authentication endpoints: register, login, me."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings


# ── Register ──────────────────────────────────────────────────────────────


def test_register_success(client):
    """POST /auth/register creates a new user and returns an access token."""
    email = f"reg-{uuid.uuid4().hex[:8]}@test.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "StrongPass123@"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_email(client, test_user, test_password):
    """Registering with an existing email returns 400."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": test_user.email, "password": test_password},
    )
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"].lower()


def test_register_weak_password(client):
    """A password that doesn't meet the policy is rejected (422)."""
    email = f"weak-{uuid.uuid4().hex[:8]}@test.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "short"},
    )
    assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────


def test_login_success(client, test_user, test_password):
    """POST /auth/login with valid credentials returns access + refresh tokens."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": test_password},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_wrong_password(client, test_user):
    """Wrong password returns 401."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "WrongPassword123@"},
    )
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    """Login with unknown email returns 401."""
    resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"nobody-{uuid.uuid4().hex[:8]}@test.com",
            "password": "Anything123@",
        },
    )
    assert resp.status_code == 401


# ── Me ────────────────────────────────────────────────────────────────────


def test_get_me_authenticated(authenticated_client, test_user):
    """GET /auth/me returns current user info."""
    resp = authenticated_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == test_user.email
    assert data["id"] == str(test_user.id)


def test_get_me_unauthenticated(client):
    """GET /auth/me without a token returns 403."""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)


def test_expired_token(client, test_user):
    """An expired JWT is rejected."""
    expired_token = jwt.encode(
        {
            "sub": str(test_user.id),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "type": "access",
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401
