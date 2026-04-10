"""
Feature gating — enforces subscription tier limits across all endpoints.
Import and use require_tier() or check_and_consume_quota() as FastAPI dependencies.
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from ..database import get_db
from ..database.models import User
from .auth import get_current_active_user

# ---------------------------------------------------------------------------
# Tier definitions (mirrors billing.py — billing.py is the authoritative source
# for quota resets; gating.py reads the current state)
# ---------------------------------------------------------------------------

TIER_HIERARCHY = {
    "free":    0,
    "starter": 1,
    "pro":     2,
    "agency":  3,
}

TIER_QUOTAS = {
    "free":    10,
    "starter": 30,
    "pro":     100,
    "agency":  99999,
}

TIER_DISPLAY = {
    "free":    "Free",
    "starter": "Starter ($29/mo)",
    "pro":     "Pro ($79/mo)",
    "agency":  "Agency ($199/mo)",
}


# ---------------------------------------------------------------------------
# Tier check dependency factory
# ---------------------------------------------------------------------------

def require_tier(minimum_tier: str):
    """
    FastAPI dependency factory. Use as:
        current_user: User = Depends(require_tier("pro"))

    Raises 403 if the user's tier is below the minimum.
    """
    def _dependency(current_user: User = Depends(get_current_active_user)):
        user_level = TIER_HIERARCHY.get(current_user.subscription_tier or "free", 0)
        required_level = TIER_HIERARCHY.get(minimum_tier, 0)

        if user_level < required_level:
            required_display = TIER_DISPLAY.get(minimum_tier, minimum_tier)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires the {required_display} plan. "
                       f"Upgrade at instaaistudio.netlify.app/upgrade",
            )
        return current_user

    return _dependency


# ---------------------------------------------------------------------------
# Monthly quota check + decrement
# ---------------------------------------------------------------------------

def check_and_consume_quota(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency. Checks that the user has remaining monthly quota,
    decrements it by 1, and auto-resets if a calendar month has passed.
    Use as:
        current_user: User = Depends(check_and_consume_quota)
    """
    # Auto-reset quota at the start of a new calendar month
    now = datetime.utcnow()
    reset_date = current_user.quota_reset_date
    if reset_date is None or now.month != reset_date.month or now.year != reset_date.year:
        tier_max = TIER_QUOTAS.get(current_user.subscription_tier or "free", 10)
        current_user.monthly_quota_remaining = tier_max
        current_user.quota_reset_date = now
        db.commit()

    if current_user.monthly_quota_remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly content quota exceeded. "
                   "Upgrade your plan to generate more content.",
        )

    current_user.monthly_quota_remaining -= 1
    db.commit()
    return current_user


# ---------------------------------------------------------------------------
# Account limit check
# ---------------------------------------------------------------------------

MAX_ACCOUNTS = {
    "free":    1,
    "starter": 1,
    "pro":     3,
    "agency":  10,
}


def check_account_limit(current_user: User, account_count: int):
    """
    Call this before allowing a user to connect a new Instagram account.
    Not a dependency — call directly with the current account count.
    """
    limit = MAX_ACCOUNTS.get(current_user.subscription_tier or "free", 1)
    if account_count >= limit:
        required = "pro" if limit < 3 else "agency"
        required_display = TIER_DISPLAY.get(required, required)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your plan allows {limit} Instagram account(s). "
                   f"Upgrade to {required_display} to connect more.",
        )
