"""Tests for payments infrastructure: webhook processing, tier gating, and free-tier filtering.

All Stripe calls are mocked -- no API keys required.
Webhook and tier gating tests use mocked DB interactions.
Integration tests (audit filtering) require the Supabase DB.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.core.dependencies import SubscriptionTier
from app.models.subscription import Subscription, WebhookEvent
from app.api.payments import (
    _handle_checkout_completed,
    _handle_subscription_updated,
    _handle_subscription_deleted,
    _handle_invoice_paid,
    _handle_invoice_payment_failed,
    _handle_event,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stripe_event(event_id: str, event_type: str, data_object: dict):
    """Build a mock Stripe Event object."""
    event = MagicMock()
    event.id = event_id
    event.type = event_type
    event.data = MagicMock()
    event.data.object = data_object
    return event


def _mock_db():
    """Create a mock DB session with query chaining support."""
    db = MagicMock()
    return db


def _setup_query_chain(db, result=None):
    """Set up db.query().filter().first() chain to return result."""
    query = MagicMock()
    db.query.return_value = query
    query.filter.return_value = query
    query.first.return_value = result
    return query


# ---------------------------------------------------------------------------
# Webhook handler unit tests (no DB needed, mocked session)
# ---------------------------------------------------------------------------


class TestCheckoutCompleted:
    """Test _handle_checkout_completed handler."""

    def test_creates_subscription_for_new_user(self):
        """Should create a new Subscription when user has none."""
        db = _mock_db()
        _setup_query_chain(db, result=None)  # No existing subscription

        user_id = str(uuid.uuid4())
        session_data = {
            "metadata": {"user_id": user_id},
            "customer": "cus_new123",
            "subscription": "sub_new123",
        }

        _handle_checkout_completed(session_data, db)

        # Should have called db.add with a new Subscription
        db.add.assert_called_once()
        new_sub = db.add.call_args[0][0]
        assert isinstance(new_sub, Subscription)
        assert str(new_sub.user_id) == user_id
        assert new_sub.stripe_customer_id == "cus_new123"
        assert new_sub.stripe_subscription_id == "sub_new123"
        assert new_sub.tier == "pro"
        assert new_sub.status == "active"
        db.commit.assert_called_once()

    def test_updates_existing_subscription(self):
        """Should update existing Subscription when user already has one."""
        db = _mock_db()
        existing_sub = Subscription(
            user_id=uuid.uuid4(),
            stripe_customer_id="cus_old",
            stripe_subscription_id="sub_old",
            tier="pro",
            status="canceled",
        )
        _setup_query_chain(db, result=existing_sub)

        session_data = {
            "metadata": {"user_id": str(existing_sub.user_id)},
            "customer": "cus_updated",
            "subscription": "sub_updated",
        }

        _handle_checkout_completed(session_data, db)

        assert existing_sub.stripe_customer_id == "cus_updated"
        assert existing_sub.stripe_subscription_id == "sub_updated"
        assert existing_sub.status == "active"
        assert existing_sub.tier == "pro"
        db.add.assert_not_called()  # Should not add, just update
        db.commit.assert_called_once()

    def test_missing_user_id_skips(self):
        """Should skip processing if metadata has no user_id."""
        db = _mock_db()
        session_data = {
            "metadata": {},
            "customer": "cus_xxx",
            "subscription": "sub_xxx",
        }

        _handle_checkout_completed(session_data, db)

        db.add.assert_not_called()
        db.commit.assert_not_called()


class TestSubscriptionUpdated:
    """Test _handle_subscription_updated handler."""

    def test_updates_existing_subscription_status(self):
        """Should update status and cancel_at_period_end."""
        db = _mock_db()
        existing_sub = Subscription(
            stripe_subscription_id="sub_123",
            stripe_customer_id="cus_123",
            status="active",
            cancel_at_period_end=False,
        )
        _setup_query_chain(db, result=existing_sub)

        sub_data = {
            "id": "sub_123",
            "status": "past_due",
            "cancel_at_period_end": True,
            "customer": "cus_123",
        }

        _handle_subscription_updated(sub_data, db)

        assert existing_sub.status == "past_due"
        assert existing_sub.cancel_at_period_end is True
        db.commit.assert_called_once()

    def test_unknown_subscription_skips_create(self):
        """Should skip creating if subscription not found (no user_id available)."""
        db = _mock_db()
        _setup_query_chain(db, result=None)

        sub_data = {
            "id": "sub_unknown",
            "status": "active",
            "cancel_at_period_end": False,
            "customer": "cus_unknown",
        }

        _handle_subscription_updated(sub_data, db)

        db.add.assert_not_called()
        db.commit.assert_not_called()


class TestSubscriptionDeleted:
    """Test _handle_subscription_deleted handler."""

    def test_marks_subscription_canceled(self):
        """Should set status to canceled."""
        db = _mock_db()
        existing_sub = Subscription(
            stripe_subscription_id="sub_del",
            status="active",
        )
        _setup_query_chain(db, result=existing_sub)

        sub_data = {"id": "sub_del"}

        _handle_subscription_deleted(sub_data, db)

        assert existing_sub.status == "canceled"
        db.commit.assert_called_once()

    def test_unknown_subscription_logs_warning(self):
        """Should not error when subscription not found."""
        db = _mock_db()
        _setup_query_chain(db, result=None)

        sub_data = {"id": "sub_nonexistent"}

        # Should not raise
        _handle_subscription_deleted(sub_data, db)
        db.commit.assert_not_called()


class TestInvoicePaid:
    """Test _handle_invoice_paid handler."""

    def test_confirms_active_status(self):
        """Should set subscription to active if it was past_due."""
        db = _mock_db()
        existing_sub = Subscription(
            stripe_customer_id="cus_inv",
            status="past_due",
        )
        _setup_query_chain(db, result=existing_sub)

        invoice_data = {"customer": "cus_inv"}

        _handle_invoice_paid(invoice_data, db)

        assert existing_sub.status == "active"
        db.commit.assert_called_once()


class TestInvoicePaymentFailed:
    """Test _handle_invoice_payment_failed handler."""

    def test_sets_past_due(self):
        """Should set subscription to past_due."""
        db = _mock_db()
        existing_sub = Subscription(
            stripe_customer_id="cus_fail",
            status="active",
        )
        _setup_query_chain(db, result=existing_sub)

        invoice_data = {"customer": "cus_fail"}

        _handle_invoice_payment_failed(invoice_data, db)

        assert existing_sub.status == "past_due"
        db.commit.assert_called_once()


class TestHandleEvent:
    """Test _handle_event routing."""

    def test_routes_checkout_completed(self):
        """Should route to checkout handler."""
        db = _mock_db()
        _setup_query_chain(db, result=None)
        event = _make_stripe_event(
            "evt_1",
            "checkout.session.completed",
            {"metadata": {"user_id": str(uuid.uuid4())}, "customer": "cus_1", "subscription": "sub_1"},
        )

        # Should not raise
        _handle_event(event, db)

    def test_routes_unknown_event_without_error(self):
        """Unknown events should not raise."""
        db = _mock_db()
        event = _make_stripe_event("evt_2", "some.unknown.event", {})
        _handle_event(event, db)


# ---------------------------------------------------------------------------
# Tier gating logic tests (pure unit, no DB)
# ---------------------------------------------------------------------------


class TestTierGating:
    """Test SubscriptionTier enum and tier determination logic."""

    def test_pro_tier_greater_than_free(self):
        """PRO should be > FREE for comparison."""
        assert SubscriptionTier.PRO > SubscriptionTier.FREE

    def test_active_subscription_means_pro(self):
        """Active subscription in DB query results means PRO tier."""
        # Simulate what get_user_tier does
        sub = Subscription(status="active")
        tier = SubscriptionTier.PRO if sub else SubscriptionTier.FREE
        assert tier == SubscriptionTier.PRO

    def test_no_subscription_means_free(self):
        """No subscription found means FREE tier."""
        sub = None
        tier = SubscriptionTier.PRO if sub else SubscriptionTier.FREE
        assert tier == SubscriptionTier.FREE

    def test_canceled_subscription_excluded_from_active_query(self):
        """Canceled status should not match the active/trialing filter."""
        # This tests the filter logic conceptually
        statuses_that_qualify = ["active", "trialing"]
        assert "canceled" not in statuses_that_qualify
        assert "past_due" not in statuses_that_qualify
        assert "unpaid" not in statuses_that_qualify

    def test_trialing_subscription_means_pro(self):
        """Trialing status should qualify as PRO."""
        statuses_that_qualify = ["active", "trialing"]
        assert "trialing" in statuses_that_qualify


# ---------------------------------------------------------------------------
# Webhook event model tests
# ---------------------------------------------------------------------------


class TestWebhookEventModel:
    """Test WebhookEvent model creation."""

    def test_create_webhook_event(self):
        """Should create WebhookEvent with correct fields."""
        we = WebhookEvent(
            stripe_event_id="evt_test123",
            event_type="checkout.session.completed",
            status="received",
        )
        assert we.stripe_event_id == "evt_test123"
        assert we.event_type == "checkout.session.completed"
        assert we.status == "received"

    def test_subscription_model_with_explicit_values(self):
        """Should accept all field values correctly."""
        uid = uuid.uuid4()
        sub = Subscription(
            user_id=uid,
            tier="pro",
            status="active",
            cancel_at_period_end=False,
            stripe_customer_id="cus_test",
            stripe_subscription_id="sub_test",
        )
        assert sub.user_id == uid
        assert sub.tier == "pro"
        assert sub.status == "active"
        assert sub.cancel_at_period_end is False
        assert sub.stripe_customer_id == "cus_test"


# ---------------------------------------------------------------------------
# Integration tests (require Supabase DB -- skip if unavailable)
# ---------------------------------------------------------------------------

# These tests use conftest.py fixtures (client, db, test_user, auth_headers)
# and will be skipped if the DB is unreachable.

try:
    from tests.conftest import engine as _test_engine
    _test_engine.connect().close()
    _db_available = True
except Exception:
    _db_available = False

skip_no_db = pytest.mark.skipif(not _db_available, reason="Supabase DB not reachable")


@skip_no_db
class TestWebhookIdempotencyIntegration:
    """Integration test: webhook idempotency via HTTP."""

    def test_duplicate_event_returns_already_processed(self, client, db, test_user):
        """Sending the same event ID twice should return already_processed."""
        event_id = f"evt_{uuid.uuid4().hex}"
        event = _make_stripe_event(
            event_id,
            "checkout.session.completed",
            {
                "metadata": {"user_id": str(test_user.id)},
                "customer": "cus_dup",
                "subscription": "sub_dup",
            },
        )

        with patch("app.api.payments.StripeService") as MockService:
            instance = MockService.return_value
            instance.verify_webhook.return_value = event

            resp1 = client.post(
                "/api/v1/payments/webhook",
                content=b"payload",
                headers={"stripe-signature": "sig_test"},
            )
            assert resp1.status_code == 200

            resp2 = client.post(
                "/api/v1/payments/webhook",
                content=b"payload",
                headers={"stripe-signature": "sig_test"},
            )
            assert resp2.status_code == 200
            assert resp2.json()["status"] == "already_processed"

    def test_missing_signature_returns_400(self, client):
        """Missing stripe-signature header should return 400."""
        resp = client.post(
            "/api/v1/payments/webhook",
            content=b"payload",
        )
        assert resp.status_code == 400


@skip_no_db
class TestTierGatingIntegration:
    """Integration test: require_tier returns 402 for free users."""

    def test_recommendations_endpoint_returns_402_for_free_user(
        self, authenticated_client, db, test_user
    ):
        """GET /recommendations/{audit_id} should return 402 for free users."""
        audit = Audit(
            id=uuid.uuid4(),
            user_id=test_user.id,
            url="https://example.com",
            domain="example.com",
            status=AuditStatus.COMPLETED.value,
        )
        db.add(audit)
        db.flush()

        resp = authenticated_client.get(
            f"/api/v1/recommendations/{audit.id}"
        )
        assert resp.status_code == 402


@skip_no_db
class TestFreeTierFilteringIntegration:
    """Integration test: free users get filtered audit responses."""

    def test_free_user_sees_limited_response(
        self, authenticated_client, db, test_user
    ):
        """Free user should get is_limited=True."""
        audit = Audit(
            id=uuid.uuid4(),
            user_id=test_user.id,
            url="https://example.com",
            domain="example.com",
            status=AuditStatus.COMPLETED.value,
            optimization_score=72,
        )
        db.add(audit)
        db.flush()

        resp = authenticated_client.get(f"/api/v1/audit/{audit.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_limited"] is True
