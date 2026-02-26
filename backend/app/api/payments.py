"""Payments API endpoints for Stripe subscription management.

Provides POST checkout session creation, POST customer portal,
GET session status polling, and POST webhook handler with
idempotent event processing.
"""

from datetime import datetime, timezone
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limiter import integration_rate_limit
from app.core.security import get_current_active_user
from app.models import Profile
from app.models.subscription import Subscription, WebhookEvent
from app.services.stripe_service import StripeService

router = APIRouter()


# --- Pydantic Schemas ---


class CreateCheckoutRequest(BaseModel):
    """Request body for creating a Stripe Checkout Session."""

    price_id: str = Field(..., pattern=r"^price_")


class CreateCheckoutResponse(BaseModel):
    """Response body with checkout URL and session ID."""

    checkout_url: str
    session_id: str


class PortalResponse(BaseModel):
    """Response body with customer portal URL."""

    portal_url: str


class SessionStatusResponse(BaseModel):
    """Response body for session status polling."""

    status: str
    subscription_id: Optional[str] = None
    customer_email: Optional[str] = None


# --- Endpoints ---


@router.post(
    "/create-checkout",
    response_model=CreateCheckoutResponse,
    dependencies=[Depends(integration_rate_limit)],
)
async def create_checkout(
    request: CreateCheckoutRequest,
    current_user: Profile = Depends(get_current_active_user),
):
    """Create a Stripe Checkout Session for subscription purchase.

    Authenticated. Rate-limited via integration_rate_limit.
    Returns a checkout URL for the frontend to redirect to.
    """
    try:
        stripe_service = StripeService()
        checkout_url, session_id = await stripe_service.create_checkout_session(
            price_id=request.price_id,
            customer_email=current_user.email,
            user_id=str(current_user.id),
        )
        logger.info(
            "Checkout session {} created for user {}",
            session_id,
            current_user.id,
        )
        return CreateCheckoutResponse(
            checkout_url=checkout_url, session_id=session_id
        )
    except stripe.StripeError as e:
        logger.error("Stripe error creating checkout: {}", str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment service error",
        )


@router.post(
    "/create-portal",
    response_model=PortalResponse,
    dependencies=[Depends(integration_rate_limit)],
)
async def create_portal(
    current_user: Profile = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Customer Portal session for self-service management.

    Authenticated. Requires an existing subscription with a Stripe customer ID.
    """
    sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == current_user.id)
        .first()
    )
    if not sub or not sub.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription",
        )

    try:
        stripe_service = StripeService()
        portal_url = await stripe_service.create_portal_session(
            sub.stripe_customer_id
        )
        logger.info(
            "Portal session created for user {}", current_user.id
        )
        return PortalResponse(portal_url=portal_url)
    except stripe.StripeError as e:
        logger.error("Stripe error creating portal: {}", str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment service error",
        )


@router.get("/session-status", response_model=SessionStatusResponse)
async def session_status(
    session_id: str,
    current_user: Profile = Depends(get_current_active_user),
):
    """Poll a Checkout Session status to confirm subscription activation.

    Used by the success page to detect when the webhook has processed.
    Handles the race condition where checkout completes before webhook fires.
    """
    try:
        stripe_service = StripeService()
        session = await stripe_service.retrieve_checkout_session(session_id)
        return SessionStatusResponse(
            status=session.status or "unknown",
            subscription_id=getattr(session, "subscription", None),
            customer_email=getattr(
                session, "customer_email", None
            )
            or (
                getattr(session, "customer_details", None)
                and getattr(session.customer_details, "email", None)
            ),
        )
    except stripe.StripeError as e:
        logger.error("Stripe error retrieving session: {}", str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment service error",
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Handle Stripe webhook events.

    Public endpoint (no auth) secured via Stripe signature verification.
    Processes subscription lifecycle events with idempotent deduplication
    via the WebhookEvent table.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header",
        )

    # Verify signature and parse event
    try:
        stripe_service = StripeService()
        event = stripe_service.verify_webhook(payload.decode(), sig_header)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    event_id = event.id
    event_type = event.type

    # Idempotency check
    existing = (
        db.query(WebhookEvent)
        .filter(WebhookEvent.stripe_event_id == event_id)
        .first()
    )
    if existing:
        logger.info("Duplicate webhook event {}, skipping", event_id)
        return {"status": "already_processed"}

    # Store event before processing
    webhook_event = WebhookEvent(
        stripe_event_id=event_id,
        event_type=event_type,
        status="received",
    )
    db.add(webhook_event)
    db.commit()

    try:
        _handle_event(event, db)
        webhook_event.status = "processed"
        db.commit()
        logger.info("Webhook event {} ({}) processed", event_id, event_type)
    except Exception as e:
        webhook_event.status = "failed"
        db.commit()
        logger.error(
            "Webhook event {} processing failed: {}", event_id, str(e)
        )

    # Always return 200 so Stripe doesn't retry for logic errors
    return {"status": "success"}


def _handle_event(event, db: Session) -> None:
    """Route a Stripe event to the appropriate handler.

    Uses upsert pattern: if subscription doesn't exist in DB, create it.
    This handles Stripe's non-guaranteed event ordering.
    """
    event_type = event.type
    data_object = event.data.object

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data_object, db)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data_object, db)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data_object, db)
    elif event_type == "invoice.paid":
        _handle_invoice_paid(data_object, db)
    elif event_type == "invoice.payment_failed":
        _handle_invoice_payment_failed(data_object, db)
    else:
        logger.info("Unhandled event type: {}", event_type)


def _handle_checkout_completed(session, db: Session) -> None:
    """Handle checkout.session.completed: create/update subscription."""
    user_id = session.get("metadata", {}).get("user_id") if isinstance(session, dict) else getattr(session, "metadata", {}).get("user_id")
    customer_id = session.get("customer") if isinstance(session, dict) else getattr(session, "customer", None)
    subscription_id = session.get("subscription") if isinstance(session, dict) else getattr(session, "subscription", None)

    if not user_id:
        logger.warning("checkout.session.completed missing user_id in metadata")
        return

    sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id)
        .first()
    )
    if sub:
        sub.stripe_customer_id = customer_id
        sub.stripe_subscription_id = subscription_id
        sub.tier = "pro"
        sub.status = "active"
        sub.updated_at = datetime.now(timezone.utc)
    else:
        sub = Subscription(
            user_id=user_id,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            tier="pro",
            status="active",
        )
        db.add(sub)
    db.commit()

    logger.info(
        "Subscription upserted for user {} (customer {})",
        user_id,
        customer_id,
    )


def _handle_subscription_updated(subscription_obj, db: Session) -> None:
    """Handle customer.subscription.updated: update subscription state."""
    stripe_sub_id = subscription_obj.get("id") if isinstance(subscription_obj, dict) else getattr(subscription_obj, "id", None)
    sub_status = subscription_obj.get("status") if isinstance(subscription_obj, dict) else getattr(subscription_obj, "status", None)
    cancel_at = subscription_obj.get("cancel_at_period_end") if isinstance(subscription_obj, dict) else getattr(subscription_obj, "cancel_at_period_end", False)
    customer_id = subscription_obj.get("customer") if isinstance(subscription_obj, dict) else getattr(subscription_obj, "customer", None)

    sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == stripe_sub_id)
        .first()
    )
    if sub:
        sub.status = sub_status or sub.status
        sub.cancel_at_period_end = bool(cancel_at)
        sub.updated_at = datetime.now(timezone.utc)
    else:
        # Upsert: create if not found (handles out-of-order delivery)
        sub = Subscription(
            stripe_subscription_id=stripe_sub_id,
            stripe_customer_id=customer_id,
            status=sub_status or "active",
            cancel_at_period_end=bool(cancel_at),
            # user_id will need to be resolved; for now set from customer
            # This path is rare and only happens with out-of-order events
        )
        # Cannot create without user_id (FK constraint), log and skip
        logger.warning(
            "subscription.updated for unknown sub {}, skipping create",
            stripe_sub_id,
        )
        return
    db.commit()

    logger.info(
        "Subscription {} updated: status={}, cancel_at_period_end={}",
        stripe_sub_id,
        sub_status,
        cancel_at,
    )


def _handle_subscription_deleted(subscription_obj, db: Session) -> None:
    """Handle customer.subscription.deleted: mark subscription canceled."""
    stripe_sub_id = subscription_obj.get("id") if isinstance(subscription_obj, dict) else getattr(subscription_obj, "id", None)

    sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == stripe_sub_id)
        .first()
    )
    if sub:
        sub.status = "canceled"
        sub.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Subscription {} canceled", stripe_sub_id)
    else:
        logger.warning(
            "subscription.deleted for unknown sub {}", stripe_sub_id
        )


def _handle_invoice_paid(invoice_obj, db: Session) -> None:
    """Handle invoice.paid: confirm subscription is active."""
    customer_id = invoice_obj.get("customer") if isinstance(invoice_obj, dict) else getattr(invoice_obj, "customer", None)

    sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_customer_id == customer_id)
        .first()
    )
    if sub and sub.status != "active":
        sub.status = "active"
        sub.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(
            "Subscription for customer {} confirmed active via invoice.paid",
            customer_id,
        )


def _handle_invoice_payment_failed(invoice_obj, db: Session) -> None:
    """Handle invoice.payment_failed: mark subscription past_due."""
    customer_id = invoice_obj.get("customer") if isinstance(invoice_obj, dict) else getattr(invoice_obj, "customer", None)

    sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_customer_id == customer_id)
        .first()
    )
    if sub:
        sub.status = "past_due"
        sub.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(
            "Subscription for customer {} marked past_due via payment_failed",
            customer_id,
        )
