"""
Stripe billing endpoints — subscriptions, checkout, webhooks, portal.
"""
import os
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

from ..database import get_db
from ..database.models import User
from .auth import get_current_active_user

router = APIRouter()
logger = logging.getLogger(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Stripe Price IDs — set these in env after creating products in Stripe dashboard
PRICE_IDS = {
    "starter": os.getenv("STRIPE_PRICE_STARTER"),
    "pro":     os.getenv("STRIPE_PRICE_PRO"),
    "agency":  os.getenv("STRIPE_PRICE_AGENCY"),
}

# Map Stripe Price ID back to tier name
PRICE_TO_TIER = {v: k for k, v in PRICE_IDS.items() if v}

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://instaaistudio.netlify.app")


# ---------------------------------------------------------------------------
# Tier definitions (single source of truth)
# ---------------------------------------------------------------------------

TIER_LIMITS = {
    "free":    {"monthly_quota": 10,    "max_accounts": 1,  "scheduling": False, "teams": False},
    "starter": {"monthly_quota": 30,    "max_accounts": 1,  "scheduling": True,  "teams": False},
    "pro":     {"monthly_quota": 100,   "max_accounts": 3,  "scheduling": True,  "teams": True},
    "agency":  {"monthly_quota": 99999, "max_accounts": 10, "scheduling": True,  "teams": True},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_customer(user: User, db: Session) -> str:
    """Return existing Stripe customer ID or create a new one."""
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        name=user.full_name or user.email,
        metadata={"user_id": str(user.id)},
    )
    user.stripe_customer_id = customer.id
    db.commit()
    return customer.id


def _apply_subscription(user: User, subscription: stripe.Subscription, db: Session):
    """Update user tier and quota from a Stripe subscription object."""
    price_id = subscription["items"]["data"][0]["price"]["id"]
    tier = PRICE_TO_TIER.get(price_id, "free")
    status = subscription["status"]  # active, past_due, canceled, etc.

    user.subscription_tier = tier if status == "active" else "free"
    user.subscription_status = status
    user.stripe_subscription_id = subscription["id"]

    if status == "active":
        limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        user.monthly_quota_remaining = limits["monthly_quota"]

    # Store period end as expiry reference
    period_end = subscription.get("current_period_end")
    if period_end:
        user.subscription_expires_at = datetime.utcfromtimestamp(period_end)

    db.commit()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

class CheckoutRequest(BaseModel):
    tier: str  # "starter" | "pro" | "agency"


@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session and return the URL."""
    if request.tier not in PRICE_IDS:
        raise HTTPException(status_code=400, detail=f"Unknown tier: {request.tier}")

    price_id = PRICE_IDS[request.tier]
    if not price_id:
        raise HTTPException(
            status_code=500,
            detail=f"STRIPE_PRICE_{request.tier.upper()} env var not set"
        )

    customer_id = _get_or_create_customer(current_user, db)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{FRONTEND_URL}/billing/cancel",
        metadata={"user_id": str(current_user.id), "tier": request.tier},
        subscription_data={"metadata": {"user_id": str(current_user.id)}},
        allow_promotion_codes=True,
    )

    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/portal")
async def create_portal_session(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe customer portal session (manage/cancel subscription)."""
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No active subscription found")

    session = stripe.billing_portal.Session.create(
        customer=current_user.stripe_customer_id,
        return_url=f"{FRONTEND_URL}/settings",
    )
    return {"portal_url": session.url}


@router.get("/subscription")
async def get_subscription(
    current_user: User = Depends(get_current_active_user),
):
    """Return current subscription state."""
    limits = TIER_LIMITS.get(current_user.subscription_tier, TIER_LIMITS["free"])
    return {
        "tier": current_user.subscription_tier,
        "status": current_user.subscription_status,
        "expires_at": current_user.subscription_expires_at,
        "quota_remaining": current_user.monthly_quota_remaining,
        "limits": limits,
    }


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Stripe webhook handler.
    Configure this URL in the Stripe dashboard:
    https://dashboard.stripe.com/webhooks → add endpoint → /api/billing/webhook
    Events to listen for: checkout.session.completed,
    customer.subscription.updated, customer.subscription.deleted,
    invoice.payment_failed
    """
    body = await request.body()

    try:
        event = stripe.Webhook.construct_event(body, stripe_signature, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info(f"Stripe webhook: {event_type}")

    if event_type == "checkout.session.completed":
        user_id = data.get("metadata", {}).get("user_id")
        subscription_id = data.get("subscription")
        if user_id and subscription_id:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user:
                subscription = stripe.Subscription.retrieve(subscription_id)
                _apply_subscription(user, subscription, db)
                logger.info(f"Upgraded user {user_id} via checkout")

    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        user_id = data.get("metadata", {}).get("user_id")
        if not user_id:
            # Fall back to looking up by stripe_subscription_id
            user = db.query(User).filter(
                User.stripe_subscription_id == data["id"]
            ).first()
        else:
            user = db.query(User).filter(User.id == int(user_id)).first()

        if user:
            if event_type == "customer.subscription.deleted":
                user.subscription_tier = "free"
                user.subscription_status = "canceled"
                user.monthly_quota_remaining = TIER_LIMITS["free"]["monthly_quota"]
                db.commit()
                logger.info(f"Downgraded user {user.id} to free (subscription canceled)")
            else:
                _apply_subscription(user, data, db)
                logger.info(f"Updated subscription for user {user.id}")

    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        if customer_id:
            user = db.query(User).filter(
                User.stripe_customer_id == customer_id
            ).first()
            if user:
                user.subscription_status = "past_due"
                db.commit()
                logger.warning(f"Payment failed for user {user.id}")

    return {"received": True}
