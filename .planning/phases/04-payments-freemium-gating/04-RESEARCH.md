# Phase 4: Payments + Freemium Gating - Research

**Researched:** 2026-02-26
**Domain:** Stripe Payments, Subscription Lifecycle, Feature Gating (FastAPI + Nuxt 3)
**Confidence:** HIGH

## Summary

Phase 4 implements a freemium subscription model with Stripe handling payment processing. The existing codebase has stub Stripe endpoints in `integrations.py` using the **legacy** `stripe.api_key` global pattern and the old `Organization` model for tier tracking. The Stripe Python SDK is already upgraded to v14.0.1 in the venv (requirements.txt still says 7.9.0 -- stale), which supports the modern `StripeClient` instance-based pattern with native async support.

The implementation requires three distinct layers: (1) a `subscriptions` table and Stripe service that manages the Checkout Session creation, Customer Portal sessions, and webhook processing; (2) a FastAPI dependency injection system (`require_tier`) that gates endpoints by subscription level; and (3) frontend integration using `@stripe/stripe-js` for redirect to Stripe-hosted Checkout and a success/cancel page flow.

The key architectural decisions are: use Stripe Checkout Sessions (not Payment Elements) for simplicity and PCI scope reduction; use the Stripe Customer Portal for self-service subscription management (cancel, update payment method); store a `subscriptions` table separate from the Organization model for proper Stripe state tracking; enforce all gating server-side via FastAPI dependencies; and process webhooks idempotently with event deduplication.

**Primary recommendation:** Use the new `StripeClient` instance pattern (not the deprecated global `stripe.api_key`), implement idempotent webhook processing with stored event IDs, and enforce all feature gating server-side via FastAPI `Depends()` -- never trust the frontend for access control.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PAY-01 | Stripe Checkout Sessions for subscription purchase flow | StripeClient.v1.checkout.sessions.create() with mode="subscription", line_items with price_id, success/cancel URLs. Redirect pattern via @stripe/stripe-js loadStripe().redirectToCheckout(). |
| PAY-02 | Stripe webhook handling for subscription lifecycle (created, updated, cancelled, payment failed) | Listen to 6 events: checkout.session.completed, customer.subscription.updated, customer.subscription.deleted, invoice.paid, invoice.payment_failed, customer.subscription.trial_will_end. Use StripeClient.parse_event_notification() for signature verification. Store processed event IDs for idempotency. |
| PAY-03 | Free tier: partial audit (crawlability category + overall score + top 3 recommendations) | Gating logic in audit detail endpoint: free users see crawlability_avg, overall optimization_score, and top 3 recommendations. Other categories and full recommendation list return 402 or filtered response. |
| PAY-04 | Paid tier: full audit across all categories + all recommendations + exports + chat + code analysis | Paid tier check via `require_tier(SubscriptionTier.PRO)` dependency on all premium endpoints. No filtering applied -- full data access. |
| PAY-05 | Feature gating enforced via FastAPI dependencies checking subscription tier | `require_tier()` dependency factory that queries subscriptions table, compares tier level, raises HTTP 402 if insufficient. Applied to: full recommendations, exports, chat, code analysis endpoints. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| stripe (Python) | 14.0.1 (installed) -> 14.4.0 (latest) | Backend Stripe API calls | Official SDK; StripeClient pattern is the modern approach; v14 has native async via httpx |
| @stripe/stripe-js | ^8.0.0 (latest: 8.8.0) | Frontend Checkout redirect | Official Stripe JS SDK; loadStripe() + redirectToCheckout() for Checkout Sessions |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SQLAlchemy (existing) | 2.0.25 | Subscription model + webhook event storage | Already in stack; add new models/migrations |
| Alembic (existing) | 1.13.1 | Database migration for subscriptions table | Next migration is 013 |
| Redis (existing) | 5.0.1 | Rate limiting by tier, webhook dedup cache | Already in stack |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Stripe Checkout Sessions | Stripe Payment Elements (inline forms) | Payment Elements increase PCI scope, require handling 3D Secure, card tokenization, error states. Checkout Sessions offload ALL payment UI to Stripe. For a SaaS subscription flow, Checkout is simpler and recommended by Stripe. |
| Stripe Customer Portal | Custom subscription management UI | Portal handles cancel, upgrade, payment method update, invoice history for free. Building custom requires handling every edge case. Use Portal for v2, custom UI in v3 if needed. |
| @stripe/stripe-js | @unlok-co/nuxt-stripe (Nuxt module) | Nuxt module wraps the official SDK with composables. Adds convenience but also adds a dependency layer. For a simple Checkout redirect flow, the official SDK is sufficient. |
| Subscriptions table | Organization.subscription_tier column (existing) | Existing column is a simple string with no Stripe metadata (subscription_id, period_end, status). A dedicated table properly tracks Stripe state and supports future multi-plan scenarios. |

**Installation:**
```bash
# Backend -- update requirements.txt to match installed version
# stripe is already 14.0.1 in venv; update pin to >=14.0.0,<15.0.0

# Frontend
cd frontend && npm install @stripe/stripe-js
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
  api/
    payments.py              # NEW: /payments/ router (checkout, portal, webhook)
  models/
    subscription.py          # NEW: Subscription + WebhookEvent models
  services/
    stripe_service.py        # NEW: StripeService wrapping StripeClient
  core/
    dependencies.py          # NEW: require_tier(), get_user_subscription()
    config.py                # ADD: STRIPE_* price IDs, portal config

frontend/
  pages/
    pricing.vue              # NEW: Pricing page with tier comparison
    checkout/
      success.vue            # NEW: Post-checkout success page
      cancel.vue             # NEW: Post-checkout cancel page
  composables/
    useStripe.ts             # NEW: loadStripe composable
    useSubscription.ts       # NEW: current user subscription state
  plugins/
    stripe.client.ts         # NEW: client-only plugin to init Stripe
```

### Pattern 1: StripeClient Instance (Not Global)
**What:** Use `StripeClient(api_key=...)` instead of `stripe.api_key = ...`
**When to use:** Every Stripe API call
**Why:** The global pattern is deprecated. Instance-based pattern avoids shared mutable state, supports async natively, and aligns with the project's existing pattern of passing `api_key=` explicitly (see LiteLLM decision).
**Example:**
```python
# Source: Stripe Python SDK README (https://github.com/stripe/stripe-python)
from stripe import StripeClient

class StripeService:
    def __init__(self):
        self.client = StripeClient(settings.STRIPE_SECRET_KEY)

    async def create_checkout_session(
        self, price_id: str, customer_email: str, user_id: str
    ) -> str:
        session = await self.client.v1.checkout.sessions.create_async(
            params={
                "mode": "subscription",
                "line_items": [{"price": price_id, "quantity": 1}],
                "customer_email": customer_email,
                "success_url": f"{settings.FRONTEND_URL}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
                "cancel_url": f"{settings.FRONTEND_URL}/pricing",
                "metadata": {"user_id": user_id},
            }
        )
        return session.url
```

### Pattern 2: Idempotent Webhook Processing
**What:** Store webhook event IDs before processing; skip duplicates.
**When to use:** Every webhook handler
**Why:** Stripe may send the same event multiple times. Without deduplication, duplicate events can create double subscriptions or race conditions.
**Example:**
```python
# Source: Stripe Webhooks docs (https://docs.stripe.com/webhooks)
@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Verify signature using StripeClient
    stripe_service = StripeService()
    event = stripe_service.client.parse_event_notification(
        payload.decode(), sig_header, settings.STRIPE_WEBHOOK_SECRET
    )

    # Idempotency check: skip if already processed
    existing = db.query(WebhookEvent).filter(
        WebhookEvent.stripe_event_id == event.id
    ).first()
    if existing:
        return {"status": "already_processed"}

    # Store event before processing
    webhook_event = WebhookEvent(
        stripe_event_id=event.id,
        event_type=event.type,
        payload=event.data,
        status="received"
    )
    db.add(webhook_event)
    db.commit()

    # Process by event type
    await _handle_event(event, db)

    webhook_event.status = "processed"
    db.commit()

    return {"status": "success"}
```

### Pattern 3: Feature Gating via FastAPI Dependencies
**What:** `require_tier()` dependency factory that checks subscription status.
**When to use:** Every endpoint that needs tier gating.
**Why:** Clean separation of billing logic from business logic. Consistent enforcement. Cannot be bypassed by frontend tricks.
**Example:**
```python
# Source: FastAPI dependency injection pattern + existing OrganizationChecker
from enum import IntEnum

class SubscriptionTier(IntEnum):
    FREE = 0
    PRO = 1

def require_tier(minimum: SubscriptionTier):
    """FastAPI dependency that enforces minimum subscription tier."""
    async def dependency(
        current_user: Profile = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> SubscriptionTier:
        sub = db.query(Subscription).filter(
            Subscription.user_id == current_user.id,
            Subscription.status.in_(["active", "trialing"]),
        ).first()

        tier = SubscriptionTier[sub.tier.upper()] if sub else SubscriptionTier.FREE
        if tier < minimum:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"This feature requires a {minimum.name.lower()} subscription",
            )
        return tier
    return dependency
```

### Pattern 4: Partial Response for Free Tier (Not 402 Block)
**What:** Free tier audit detail returns partial data (crawlability + overall score + top 3 recs), not a full block.
**When to use:** Audit detail endpoint.
**Why:** PAY-03 specifies free users SEE crawlability scores and top 3 recommendations. Blocking the entire endpoint would prevent the "aha moment". Instead, filter the response server-side.
**Example:**
```python
@router.get("/{audit_id}")
def get_audit(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    audit = _get_audit_for_user(audit_id, db, current_user)
    tier = _get_user_tier(current_user, db)

    if tier < SubscriptionTier.PRO:
        # Free tier: filter response
        return _build_free_tier_response(audit, db)
    else:
        return _build_full_response(audit, db)
```

### Anti-Patterns to Avoid
- **Client-side gating only:** Never rely on the frontend to hide premium features. A user can inspect network requests and access gated endpoints directly. ALL gating must be server-side.
- **Global stripe.api_key:** The existing stub uses `stripe.api_key = settings.STRIPE_SECRET_KEY` at module level. This is the deprecated pattern. Replace with `StripeClient` instance.
- **Webhook handlers that assume event ordering:** Stripe does NOT guarantee delivery order. `invoice.paid` can arrive before `customer.subscription.created`. Each handler must fetch current state from Stripe if needed.
- **Storing tier on Organization only:** The existing `Organization.subscription_tier` string column has no Stripe metadata. Use a proper `Subscription` model that tracks `stripe_subscription_id`, `status`, `current_period_end`, `cancel_at_period_end`.
- **Processing webhooks synchronously in the handler:** Return 200 immediately after signature verification and event storage. Process complex logic (email notifications, etc.) asynchronously if needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Payment UI / card forms | Custom payment form | Stripe Checkout Sessions (hosted page) | PCI compliance, 3D Secure, international payment methods, fraud detection -- all handled by Stripe |
| Subscription management UI | Custom cancel/upgrade/billing page | Stripe Customer Portal | Handles cancel, upgrade, payment method update, invoice history. Configurable in Stripe Dashboard. |
| Webhook signature verification | Custom HMAC verification | `StripeClient.parse_event_notification()` | Timing-safe comparison, handles signature versioning, validates timestamp tolerance (5 min default) |
| Subscription state machine | Custom status tracking logic | Stripe's subscription status field + webhooks | Stripe manages the `trialing -> active -> past_due -> canceled` lifecycle. Your DB just mirrors it. |
| Payment retry logic | Custom retry scheduler for failed payments | Stripe Smart Retries (configured in Dashboard) | Stripe uses ML to pick optimal retry timing. Attempting to build this custom is futile. |
| Proration on plan changes | Custom proration calculator | Stripe's built-in proration | Set `proration_behavior` on subscription update. Stripe handles credit/debit calculations. |

**Key insight:** Stripe is a state machine for subscriptions. Your backend is a **mirror** of Stripe's state, not the source of truth. When in doubt, fetch the current subscription status from Stripe's API rather than relying on your local database.

## Common Pitfalls

### Pitfall 1: Webhook Event Ordering
**What goes wrong:** `customer.subscription.updated` arrives before `checkout.session.completed`. Your handler crashes because the subscription record does not exist in your database yet.
**Why it happens:** Stripe explicitly does not guarantee delivery order. Events can arrive out of sequence, be delayed, or be duplicated.
**How to avoid:** Each webhook handler must be self-contained. For `customer.subscription.updated`, create the subscription record if it does not exist (upsert pattern). Never assume another event has already been processed.
**Warning signs:** Errors like "Subscription not found" in webhook handler logs.

### Pitfall 2: Missing Webhook Events
**What goes wrong:** Your database subscription status diverges from Stripe's actual state. A user cancelled but still has access, or a payment failed but access was not revoked.
**Why it happens:** Webhook delivery can fail (your server was down, returned non-2xx, timed out). Stripe retries for up to 3 days, but if your endpoint is consistently failing, events are dropped.
**How to avoid:** Implement a daily reconciliation job that queries Stripe's API for all active subscriptions and compares against your database. Use `stripe.v1.subscriptions.list()` with `status="all"`.
**Warning signs:** Customer complaints about access after cancellation; revenue leakage from cancelled subscriptions still active.

### Pitfall 3: Free Tier Gives Away Too Little
**What goes wrong:** Free users get only crawlability scores, which is not impressive enough to demonstrate value. They never experience the "aha moment" and churn without converting.
**Why it happens:** The gate is placed at a feature boundary rather than at the value realization moment.
**How to avoid:** Per PAY-03, free tier shows: (a) overall optimization score, (b) crawlability category breakdown with all criterion scores, (c) top 3 recommendations with full detail. The "teaser" is showing that 15+ more recommendations exist with blurred previews. This gives enough value to demonstrate the product while clearly showing what upgrade unlocks.
**Warning signs:** Free users complete an audit and never return. Conversion rate below 1% after 90 days.

### Pitfall 4: Hardcoded Stripe Price IDs
**What goes wrong:** Price IDs are hardcoded in endpoint handlers (as in the current stub: `prices = {"pro": "price_pro_monthly"}`). When switching between test/live mode, or updating prices, code changes are required.
**How to avoid:** Store price IDs in Settings (loaded from .env). Add `STRIPE_PRICE_PRO_MONTHLY` and `STRIPE_PRICE_PRO_YEARLY` to config.py. The existing pattern of using pydantic-settings for configuration applies here.
**Warning signs:** Tests using production price IDs; deployment issues when price IDs differ between environments.

### Pitfall 5: Not Handling `invoice.payment_failed`
**What goes wrong:** A subscription payment fails (card expired, insufficient funds), but the user retains full access. Revenue leakage accumulates silently.
**Why it happens:** Developers implement happy-path events (`checkout.session.completed`, `invoice.paid`) and forget failure events.
**How to avoid:** Handle `invoice.payment_failed` explicitly. When received, update subscription status to `past_due` in your database. Optionally notify the user. Stripe will retry automatically via Smart Retries, and when the retry succeeds, `invoice.paid` will fire to restore `active` status.
**Warning signs:** Subscriptions in `past_due` state in Stripe but `active` in your database.

### Pitfall 6: Race Condition Between Webhook and Success Page
**What goes wrong:** User completes checkout and is redirected to `/checkout/success`, but the webhook has not yet arrived. The frontend checks subscription status and shows "free" tier.
**Why it happens:** Webhooks are asynchronous. There is no guarantee the webhook arrives before the user's browser loads the success page.
**How to avoid:** On the success page, poll the backend for subscription status with a reasonable timeout (5-10 seconds). Alternatively, use the Checkout Session ID from the URL to query Stripe directly: `GET /api/v1/payments/session-status?session_id=cs_xxx`. The backend calls `stripe.v1.checkout.sessions.retrieve()` to get the actual session status. This is faster and more reliable than waiting for the webhook.
**Warning signs:** Users seeing "free tier" on the success page after paying.

## Code Examples

### 1. Subscription Model (SQLAlchemy)
```python
# backend/app/models/subscription.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, unique=True)
    stripe_customer_id = Column(String, nullable=False, index=True)
    stripe_subscription_id = Column(String, nullable=False, unique=True, index=True)
    tier = Column(String, nullable=False, default="pro")  # pro (only one paid tier for v2)
    status = Column(String, nullable=False, default="active")  # active, past_due, canceled, trialing, unpaid
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stripe_event_id = Column(String, nullable=False, unique=True, index=True)
    event_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="received")  # received, processed, failed
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

### 2. StripeService (Backend)
```python
# backend/app/services/stripe_service.py
from stripe import StripeClient
from app.core.config import settings

class StripeService:
    def __init__(self):
        self.client = StripeClient(settings.STRIPE_SECRET_KEY)

    async def create_checkout_session(
        self, price_id: str, customer_email: str, user_id: str
    ) -> str:
        """Create Stripe Checkout Session for subscription."""
        session = await self.client.v1.checkout.sessions.create_async(
            params={
                "mode": "subscription",
                "line_items": [{"price": price_id, "quantity": 1}],
                "customer_email": customer_email,
                "success_url": f"{settings.FRONTEND_URL}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
                "cancel_url": f"{settings.FRONTEND_URL}/pricing",
                "metadata": {"user_id": user_id},
            }
        )
        return session.url

    async def create_portal_session(self, stripe_customer_id: str) -> str:
        """Create Stripe Customer Portal session for self-service management."""
        session = await self.client.v1.billing_portal.sessions.create_async(
            params={
                "customer": stripe_customer_id,
                "return_url": f"{settings.FRONTEND_URL}/settings",
            }
        )
        return session.url

    def verify_webhook(self, payload: str, sig_header: str):
        """Verify webhook signature and parse event."""
        return self.client.parse_event_notification(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )

    async def retrieve_checkout_session(self, session_id: str):
        """Retrieve a Checkout Session by ID (for success page polling)."""
        return await self.client.v1.checkout.sessions.retrieve_async(session_id)
```

### 3. Frontend Stripe Redirect (Nuxt 3)
```typescript
// frontend/composables/useStripe.ts
import { loadStripe } from '@stripe/stripe-js'

const stripePromise = loadStripe(useRuntimeConfig().public.stripePublishableKey)

export function useStripe() {
  const { apiFetch } = useApiFetch()

  async function redirectToCheckout(priceId: string) {
    // 1. Create session on backend
    const { checkout_url } = await apiFetch('/payments/create-checkout', {
      method: 'POST',
      body: { price_id: priceId },
    })

    // 2. Redirect to Stripe-hosted checkout
    window.location.href = checkout_url
  }

  async function redirectToPortal() {
    const { portal_url } = await apiFetch('/payments/create-portal', {
      method: 'POST',
    })
    window.location.href = portal_url
  }

  return { redirectToCheckout, redirectToPortal }
}
```

### 4. Settings Additions
```python
# Add to backend/app/core/config.py Settings class
# Stripe Products & Prices
STRIPE_PRICE_PRO_MONTHLY: str = ""       # price_xxx from Stripe Dashboard
STRIPE_PRICE_PRO_YEARLY: str = ""        # price_xxx from Stripe Dashboard
STRIPE_PORTAL_CONFIG_ID: str = ""        # bpc_xxx from Stripe Dashboard
FRONTEND_URL: str = "http://localhost:3000"  # For success/cancel URLs
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `stripe.api_key = "sk_..."` (global) | `StripeClient("sk_...")` (instance) | Stripe Python SDK v8 (2024) | No global mutable state; async support; thread-safe |
| `stripe.checkout.Session.create()` | `client.v1.checkout.sessions.create_async()` | Stripe Python SDK v8+ | Proper async/await; no blocking in FastAPI event loop |
| `stripe.Webhook.construct_event()` | `client.parse_event_notification()` | Stripe Python SDK v8+ | Cleaner API; same security (HMAC-SHA256 verification) |
| `stripe.error.StripeError` | `stripe.StripeError` (same) | Unchanged | Error handling remains consistent |
| `stripe.billing_portal.Session` | `client.v1.billing_portal.sessions` | Stripe Python SDK v8+ | Instance-based; same functionality |

**Deprecated/outdated:**
- `stripe.api_key` global pattern: Still works but marked for deprecation. New API endpoints will ONLY be accessible via StripeClient.
- `stripe.error` module: Renamed but available for backward compat.
- The existing `integrations.py` stub uses ALL deprecated patterns and must be replaced.

## Open Questions

1. **Single tier (Pro) vs. two tiers (Pro + Team)?**
   - What we know: REQUIREMENTS.md specifies PAY-03 (free) and PAY-04 (paid). ARCHITECTURE.md research suggested three tiers (Free/Pro/Team).
   - What's unclear: Whether v2 needs a Team tier or just Pro.
   - Recommendation: Start with **two tiers only** (Free + Pro) for v2. A Team tier adds complexity (team management, seat billing) without clear need yet. Add Team tier when multi-site management (DASH-05) is implemented. This simplifies: one Stripe Price, one tier check, one upgrade path.

2. **Pricing amount?**
   - What we know: ARCHITECTURE.md suggested $49/mo Pro, $149/mo Team.
   - What's unclear: Final pricing is a business decision, not a technical one.
   - Recommendation: Configure price IDs in `.env`, not in code. The Stripe Dashboard is where prices are created and managed. The backend only needs the price_id string. For testing, use Stripe's test mode prices.

3. **Existing Organization.subscription_tier column?**
   - What we know: `Organization` model has `subscription_tier` column. `OrganizationChecker` in `security.py` uses it. Profile.org_id links users to orgs.
   - What's unclear: Whether to keep Organization-based gating or switch to user-based.
   - Recommendation: Add a `Subscription` model keyed by `user_id`. For v2, each user has their own subscription. The Organization model stays for future team features but is not the source of truth for billing. Deprecate `OrganizationChecker.required_tier` in favor of the new `require_tier()` dependency.

4. **What happens to audits started as free when user upgrades mid-audit?**
   - What we know: Audits run as Celery background tasks (10-60 seconds).
   - What's unclear: Whether a free-tier audit in progress should retroactively get full data if the user upgrades.
   - Recommendation: Gating is applied at **read time** (when the user views results), not at **write time** (when the audit runs). The audit pipeline always runs the full pipeline regardless of tier. Gating filters what the user can SEE. This simplifies the pipeline and means upgrading instantly unlocks full results for all past audits.

## Sources

### Primary (HIGH confidence)
- Stripe Python SDK v14 README - StripeClient pattern, async support: https://github.com/stripe/stripe-python
- Stripe Checkout Sessions API - Create session params: https://docs.stripe.com/api/checkout/sessions/create?lang=python
- Stripe Subscription Webhooks - Complete event list and lifecycle: https://docs.stripe.com/billing/subscriptions/webhooks
- Stripe Webhooks - Signature verification, idempotency, retry behavior: https://docs.stripe.com/webhooks
- Stripe Customer Portal - Self-service subscription management: https://docs.stripe.com/customer-management/integrate-customer-portal
- Stripe Build Subscriptions - End-to-end subscription integration guide: https://docs.stripe.com/billing/subscriptions/build-subscriptions
- `pip index versions stripe` - v14.4.0 latest, v14.0.1 installed (verified 2026-02-26)

### Secondary (MEDIUM confidence)
- FastAPI + Stripe integration patterns: https://www.fast-saas.com/blog/fastapi-stripe-integration/
- Stripe + Supabase + FastAPI subscription implementation: https://medium.com/@ojasskapre/implementing-stripe-subscriptions-with-supabase-next-js-and-fastapi-666e1aada1b5
- Stripe webhook best practices (Stigg): https://www.stigg.io/blog-posts/best-practices-i-wish-we-knew-when-integrating-stripe-webhooks
- Hooklistener webhook guide: https://www.hooklistener.com/learn/receiving-stripe-webhooks

### Existing Project Research (HIGH confidence)
- `.planning/research/STACK.md` - Stripe upgrade recommendation, @stripe/stripe-js selection
- `.planning/research/ARCHITECTURE.md` - Subscription data model, gating pattern, tier structure
- `.planning/research/PITFALLS.md` - Pitfall 6 (freemium miscalibration), Pitfall 7 (webhook unreliability)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Stripe SDKs verified via pip/npm, versions confirmed, official docs referenced
- Architecture: HIGH - Patterns derived from official Stripe docs + existing codebase analysis, aligned with project conventions
- Pitfalls: HIGH - Based on Stripe official docs (event ordering, retry behavior) + project-specific research (PITFALLS.md)

**Research date:** 2026-02-26
**Valid until:** 2026-03-26 (Stripe SDKs are stable; patterns unlikely to change within 30 days)
