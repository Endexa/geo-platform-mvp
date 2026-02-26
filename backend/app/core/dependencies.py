"""Feature gating dependencies for subscription tier enforcement.

Provides SubscriptionTier enum, get_user_tier() helper, and require_tier()
factory for FastAPI Depends() injection. Queries the Subscription model
(not Organization.subscription_tier) for real Stripe subscription state.
"""

from enum import IntEnum

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.profile import Profile
from app.models.subscription import Subscription


class SubscriptionTier(IntEnum):
    """Subscription tiers ordered by access level."""

    FREE = 0
    PRO = 1


async def get_user_tier(
    current_user: Profile = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SubscriptionTier:
    """Determine the user's subscription tier.

    Non-blocking: returns the tier without raising errors.
    Queries the Subscription table for an active or trialing subscription.

    Returns:
        SubscriptionTier.PRO if active subscription found, FREE otherwise.
    """
    sub = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.status.in_(["active", "trialing"]),
        )
        .first()
    )
    if sub:
        return SubscriptionTier.PRO
    return SubscriptionTier.FREE


def require_tier(minimum: SubscriptionTier):
    """Factory function returning a FastAPI dependency that enforces minimum tier.

    Usage:
        @router.get("/premium", dependencies=[Depends(require_tier(SubscriptionTier.PRO))])

    Raises:
        HTTPException 402 if user's tier is below the required minimum.
    """

    async def _check_tier(
        current_user: Profile = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> SubscriptionTier:
        sub = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == current_user.id,
                Subscription.status.in_(["active", "trialing"]),
            )
            .first()
        )
        tier = SubscriptionTier.PRO if sub else SubscriptionTier.FREE

        if tier < minimum:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    f"This feature requires a {minimum.name.lower()} subscription"
                ),
            )
        return tier

    return _check_tier
