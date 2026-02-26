"""Stripe service using the modern StripeClient instance pattern.

Wraps Stripe SDK v14+ StripeClient with async methods for
checkout sessions, customer portal, webhook verification, and session retrieval.
Does NOT use the deprecated global stripe.api_key pattern.
"""

from stripe import StripeClient

from app.core.config import settings


class StripeService:
    """Service for Stripe payment operations using StripeClient."""

    def __init__(self):
        """Initialize with StripeClient instance (not deprecated global)."""
        self.client = StripeClient(settings.STRIPE_SECRET_KEY)

    async def create_checkout_session(
        self, price_id: str, customer_email: str, user_id: str
    ) -> tuple[str, str]:
        """Create a Stripe Checkout Session for subscription purchase.

        Args:
            price_id: Stripe price ID (e.g. price_xxx).
            customer_email: Email for the checkout session.
            user_id: Internal user UUID to store in session metadata.

        Returns:
            Tuple of (checkout_url, session_id).
        """
        session = await self.client.v1.checkout.sessions.create_async(
            params={
                "mode": "subscription",
                "line_items": [{"price": price_id, "quantity": 1}],
                "customer_email": customer_email,
                "success_url": (
                    f"{settings.FRONTEND_URL}/checkout/success"
                    "?session_id={CHECKOUT_SESSION_ID}"
                ),
                "cancel_url": f"{settings.FRONTEND_URL}/pricing",
                "metadata": {"user_id": user_id},
            }
        )
        return session.url, session.id

    async def create_portal_session(self, stripe_customer_id: str) -> str:
        """Create a Stripe Customer Portal session for self-service management.

        Args:
            stripe_customer_id: The Stripe customer ID (cus_xxx).

        Returns:
            Portal session URL.
        """
        params = {
            "customer": stripe_customer_id,
            "return_url": f"{settings.FRONTEND_URL}/settings",
        }
        if settings.STRIPE_PORTAL_CONFIG_ID:
            params["configuration"] = settings.STRIPE_PORTAL_CONFIG_ID

        session = await self.client.v1.billing_portal.sessions.create_async(
            params=params
        )
        return session.url

    def verify_webhook(self, payload: str, sig_header: str):
        """Verify a Stripe webhook signature and parse the event.

        Args:
            payload: Raw request body as a string.
            sig_header: Value of the stripe-signature header.

        Returns:
            Parsed Stripe Event object with full event data.

        Raises:
            stripe.SignatureVerificationError: If signature is invalid.
            ValueError: If payload is malformed.
        """
        return self.client.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )

    async def retrieve_checkout_session(self, session_id: str):
        """Retrieve a Checkout Session by ID.

        Args:
            session_id: The Stripe Checkout Session ID (cs_xxx).

        Returns:
            The Stripe Checkout Session object.
        """
        return await self.client.v1.checkout.sessions.retrieve_async(
            session_id
        )
