from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from uuid import UUID
from app.core.database import get_db
from app.core.config import settings
from app.models import Recommendation, Organization, Profile
from app.services.jira_service import JiraService
from app.core.security import get_current_active_user
from app.core.rate_limiter import standard_rate_limit, integration_rate_limit
from app.core.validators import SecureJiraRequest, SecureBaseModel
from loguru import logger
import stripe
import hmac
import hashlib

router = APIRouter()
stripe.api_key = settings.STRIPE_SECRET_KEY


# Jira Integration
class CreateJiraTicketRequest(SecureJiraRequest):
    """Secure request for Jira ticket creation (inherits validation)"""
    pass


@router.post("/jira/create-ticket", dependencies=[Depends(integration_rate_limit)])
async def create_jira_ticket(
    request: CreateJiraTicketRequest,
    db: Session = Depends(get_db),
    # Uncomment when authentication is enabled:
    # current_user: Profile = Depends(get_current_active_user)
):
    """
    Create a Jira ticket for a recommendation.

    **Security Features:**
    - Rate limited: 20 integrations per minute
    - Input validation: UUID and project key validated
    - Audit logged: All Jira ticket creations logged

    **Authentication:** Currently optional for MVP.
    In production, this requires authentication and org membership verification.
    """
    logger.info(f"Jira ticket creation requested: recommendation={request.recommendation_id}, project={request.project_key}")

    recommendation = db.query(Recommendation).filter(
        Recommendation.id == request.recommendation_id
    ).first()

    if not recommendation:
        logger.warning(f"Recommendation not found: {request.recommendation_id}")
        raise HTTPException(status_code=404, detail="Recommendation not found")

    if recommendation.jira_ticket_id:
        logger.info(f"Jira ticket already exists: {recommendation.jira_ticket_id}")
        return {
            "message": "Jira ticket already exists",
            "ticket_id": recommendation.jira_ticket_id
        }

    # Create Jira ticket
    try:
        jira_service = JiraService()
        ticket_id = await jira_service.create_ticket(
            project_key=request.project_key,
            summary=recommendation.issue,
            description=recommendation.action_plan,
            priority=recommendation.severity
        )

        # Update recommendation
        recommendation.jira_ticket_id = ticket_id
        db.commit()

        logger.info(f"Jira ticket created: {ticket_id} for recommendation {recommendation.id}")

        return {
            "message": "Jira ticket created",
            "ticket_id": ticket_id,
            "recommendation_id": str(recommendation.id)
        }
    except Exception as e:
        logger.error(f"Jira ticket creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create Jira ticket")


# Stripe Integration
class CreateCheckoutSessionRequest(SecureBaseModel):
    """Secure request for Stripe checkout session"""
    org_id: UUID
    tier: str = Field(..., pattern=r'^(pro|enterprise)$')


@router.post("/stripe/create-checkout", dependencies=[Depends(integration_rate_limit)])
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    db: Session = Depends(get_db),
    # Uncomment when authentication is enabled:
    # current_user: Profile = Depends(get_current_active_user)
):
    """
    Create a Stripe checkout session for subscription upgrade.

    **Security Features:**
    - Rate limited: 20 integrations per minute
    - Input validation: Org ID and tier validated
    - Audit logged: All payment session creations logged

    **Authentication:** Currently optional for MVP.
    In production, this requires authentication and org admin permissions.

    **IMPORTANT:** In production, verify that current_user is an admin
    of the organization before allowing payment operations.
    """
    logger.info(f"Stripe checkout session requested: org={request.org_id}, tier={request.tier}")

    organization = db.query(Organization).filter(
        Organization.id == request.org_id
    ).first()

    if not organization:
        logger.warning(f"Organization not found: {request.org_id}")
        raise HTTPException(status_code=404, detail="Organization not found")

    # Price mapping (MVP - hardcoded)
    # TODO: Move to settings or database in production
    prices = {
        "pro": "price_pro_monthly",  # Replace with actual Stripe price ID
        "enterprise": "price_enterprise_monthly"
    }

    if request.tier not in prices:
        logger.warning(f"Invalid tier requested: {request.tier}")
        raise HTTPException(status_code=400, detail="Invalid tier")

    try:
        checkout_session = stripe.checkout.Session.create(
            customer=organization.stripe_customer_id if organization.stripe_customer_id else None,
            line_items=[{
                "price": prices[request.tier],
                "quantity": 1,
            }],
            mode="subscription",
            success_url=f"{settings.CORS_ORIGINS[0]}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.CORS_ORIGINS[0]}/pricing",
            metadata={
                "org_id": str(organization.id),
                "tier": request.tier
            }
        )

        logger.info(f"Stripe checkout session created: {checkout_session.id} for org {organization.id}")

        return {
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id
        }

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=500, detail="Payment service error")
    except Exception as e:
        logger.error(f"Checkout session creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Stripe webhook events.
    Updates subscription tier on successful checkout.

    **Security Features:**
    - Webhook signature verification (HMAC)
    - Payload validation
    - Audit logged: All webhook events logged
    - Idempotency: Handles duplicate events gracefully

    **IMPORTANT:** This endpoint is public but secured via webhook signatures.
    Never process webhook events without signature verification.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        logger.warning("Stripe webhook received without signature")
        raise HTTPException(status_code=400, detail="Missing signature")

    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.error("Stripe webhook secret not configured")
        raise HTTPException(status_code=500, detail="Webhook not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"Stripe webhook received: type={event['type']}, id={event['id']}")
    except ValueError as e:
        logger.warning(f"Stripe webhook invalid payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.warning(f"Stripe webhook signature verification failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle checkout.session.completed
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        try:
            org_id = session.get("metadata", {}).get("org_id")
            tier = session.get("metadata", {}).get("tier")
            customer_id = session.get("customer")

            if not org_id or not tier:
                logger.error(f"Webhook missing metadata: org_id={org_id}, tier={tier}")
                raise HTTPException(status_code=400, detail="Missing metadata")

            # Update organization
            organization = db.query(Organization).filter(Organization.id == org_id).first()
            if organization:
                old_tier = organization.subscription_tier
                organization.subscription_tier = tier
                organization.stripe_customer_id = customer_id
                db.commit()

                logger.info(f"Organization subscription updated: org={org_id}, {old_tier} -> {tier}")
            else:
                logger.warning(f"Organization not found for webhook: {org_id}")
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            # Don't raise exception - acknowledge receipt but log error
            # Stripe will retry if we return non-2xx

    # Handle other webhook events
    elif event["type"] == "customer.subscription.deleted":
        session = event["data"]["object"]
        customer_id = session.get("customer")

        if customer_id:
            organization = db.query(Organization).filter(
                Organization.stripe_customer_id == customer_id
            ).first()
            if organization:
                organization.subscription_tier = "free"
                db.commit()
                logger.info(f"Organization subscription cancelled: org={organization.id}")

    return {"status": "success"}
