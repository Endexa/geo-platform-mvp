"""Subscription and WebhookEvent models for Stripe payment integration.

Subscription tracks a user's Stripe subscription state (tier, status, period).
WebhookEvent provides idempotent webhook processing via stored event IDs.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.core.database import Base


class Subscription(Base):
    """Tracks a user's Stripe subscription state."""

    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id"),
        unique=True,
        nullable=False,
    )
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(
        String, unique=True, nullable=True, index=True
    )
    tier = Column(String, nullable=False, default="pro")
    status = Column(
        String, nullable=False, default="active"
    )  # active, past_due, canceled, trialing, unpaid
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class WebhookEvent(Base):
    """Stores processed Stripe webhook event IDs for idempotency."""

    __tablename__ = "webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stripe_event_id = Column(String, unique=True, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    status = Column(
        String, nullable=False, default="received"
    )  # received, processed, failed
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
