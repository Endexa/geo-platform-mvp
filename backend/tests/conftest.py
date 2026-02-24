"""Shared test fixtures using the real Supabase PostgreSQL database.

Tests run against Supabase to ensure real integration.
Each test gets its own DB session with transaction rollback for isolation.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import SecurityManager
from app.main import app
from app.models.profile import Profile

# Use the real Supabase DATABASE_URL from settings / env
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db():
    """Provide a transactional DB session that rolls back after each test.

    Uses nested transactions (SAVEPOINT) so the test never commits
    permanent data to Supabase.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Start a SAVEPOINT so session.commit() inside application code
    # doesn't actually commit to the outer transaction.
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        nonlocal nested
        if transaction.nested and not transaction._parent.nested:
            nested = connection.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db: Session):
    """FastAPI TestClient with the DB dependency overridden to use the test session."""

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def test_password() -> str:
    """A password that satisfies the password policy (12+ chars, upper, lower, digit, special)."""
    return "TestPassword123@"


@pytest.fixture()
def test_user(db: Session, test_password: str) -> Profile:
    """Create a test user directly in the DB and return the Profile."""
    user = Profile(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=SecurityManager.hash_password(test_password),
        full_name="Test User",
        is_active=True,
        role="member",
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture()
def access_token(test_user: Profile) -> str:
    """Create a valid JWT access token for the test user."""
    return SecurityManager.create_access_token(data={"sub": str(test_user.id)})


@pytest.fixture()
def auth_headers(access_token: str) -> dict:
    """Authorization headers with Bearer token."""
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture()
def authenticated_client(client: TestClient, auth_headers: dict):
    """A TestClient pre-configured with auth headers via a helper wrapper."""

    class AuthClient:
        """Thin wrapper that injects auth headers into every request."""

        def __init__(self, tc: TestClient, headers: dict):
            self._tc = tc
            self._headers = headers

        def get(self, url, **kw):
            kw.setdefault("headers", {}).update(self._headers)
            return self._tc.get(url, **kw)

        def post(self, url, **kw):
            kw.setdefault("headers", {}).update(self._headers)
            return self._tc.post(url, **kw)

        def put(self, url, **kw):
            kw.setdefault("headers", {}).update(self._headers)
            return self._tc.put(url, **kw)

        def delete(self, url, **kw):
            kw.setdefault("headers", {}).update(self._headers)
            return self._tc.delete(url, **kw)

    return AuthClient(client, auth_headers)
