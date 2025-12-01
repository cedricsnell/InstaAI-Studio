"""
Instagram insights and AI analysis endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from ..database import get_db
from ..database.models import InstagramAccount, InsightsCache, InstagramPost, User
from .auth import get_current_active_user
from ..instagram.graph_api import get_instagram_api
from ..ai import analyze_instagram_insights

router = APIRouter()
logger = logging.getLogger(__name__)

# Cache expiry: 6 hours
INSIGHTS_CACHE_HOURS = 6


class InsightsResponse(BaseModel):
    account_insights: Dict[str, Any]
    ai_recommendations: Dict[str, Any]
    cached_at: datetime
    expires_at: datetime


class CampaignGoal(BaseModel):
    type: str  # awareness, traffic, conversions, engagement
    product_name: Optional[str] = None
    product_price: Optional[float] = None
    target_audience: Optional[str] = None
    budget: Optional[float] = None


@router.get("/{account_id}", response_model=InsightsResponse)
async def get_insights(
    account_id: int,
    force_refresh: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get Instagram insights and AI recommendations for an account.

    This endpoint:
    1. Checks if cached insights exist and are valid
    2. If cache expired or force_refresh, fetches fresh data from Instagram API
    3. Runs AI analysis using Claude
    4. Caches results for 6 hours
    5. Saves posts to database for future reference

    Args:
        account_id: Instagram account ID
        force_refresh: Force refresh even if cache is valid
        current_user: Authenticated user (injected)
        db: Database session (injected)

    Returns:
        Insights data + AI recommendations
    """
    # Verify account belongs to user
    account = db.query(InstagramAccount).filter(
        InstagramAccount.id == account_id,
        InstagramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Instagram account not found")

    # Check for cached insights
    if not force_refresh:
        cache = db.query(InsightsCache).filter(
            InsightsCache.instagram_account_id == account_id,
            InsightsCache.expires_at > datetime.utcnow()
        ).order_by(InsightsCache.cached_at.desc()).first()

        if cache:
            logger.info(f"Returning cached insights for account {account.username}")
            return {
                "account_insights": cache.insights_data,
                "ai_recommendations": cache.ai_recommendations or {},
                "cached_at": cache.cached_at,
                "expires_at": cache.expires_at
            }

    # Fetch fresh insights from Instagram
    logger.info(f"Fetching fresh insights for account {account.username}")

    try:
        api = get_instagram_api()

        # Fetch comprehensive insights
        insights_data = await api.get_full_insights_data(
            instagram_user_id=account.instagram_user_id,
            access_token=account.access_token,
            limit_media=50
        )

        # Update account info
        account.followers_count = insights_data["account"].get("followers_count", 0)
        account.media_count = insights_data["account"].get("media_count", 0)
        account.last_synced_at = datetime.utcnow()

        # Save posts to database
        _save_posts_to_database(db, account.id, insights_data.get("media", []))

        # Run AI analysis
        logger.info("Running AI analysis...")
        ai_recommendations = analyze_instagram_insights(insights_data)

        # Cache results
        cache_entry = InsightsCache(
            instagram_account_id=account_id,
            insights_data=insights_data,
            ai_recommendations=ai_recommendations,
            cached_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=INSIGHTS_CACHE_HOURS)
        )

        db.add(cache_entry)
        db.commit()
        db.refresh(cache_entry)

        logger.info(f"Successfully cached insights for {account.username}")

        return {
            "account_insights": insights_data,
            "ai_recommendations": ai_recommendations,
            "cached_at": cache_entry.cached_at,
            "expires_at": cache_entry.expires_at
        }

    except Exception as e:
        logger.error(f"Failed to fetch insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch insights: {str(e)}"
        )


@router.post("/{account_id}/analyze", response_model=Dict[str, Any])
async def analyze_with_goal(
    account_id: int,
    goal: CampaignGoal,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Analyze Instagram insights with a specific campaign goal.

    This generates tailored recommendations based on the campaign goal
    (e.g., awareness, conversions, engagement).

    Args:
        account_id: Instagram account ID
        goal: Campaign goal details
        current_user: Authenticated user (injected)
        db: Database session (injected)

    Returns:
        AI recommendations tailored to the campaign goal
    """
    # Verify account belongs to user
    account = db.query(InstagramAccount).filter(
        InstagramAccount.id == account_id,
        InstagramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Instagram account not found")

    # Get latest cached insights
    cache = db.query(InsightsCache).filter(
        InsightsCache.instagram_account_id == account_id
    ).order_by(InsightsCache.cached_at.desc()).first()

    if not cache:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No insights data available. Fetch insights first using GET /{account_id}"
        )

    # Run AI analysis with campaign goal
    logger.info(f"Analyzing insights with goal: {goal.type}")
    ai_recommendations = analyze_instagram_insights(
        insights_data=cache.insights_data,
        campaign_goal=goal.dict(exclude_none=True)
    )

    return ai_recommendations


def _save_posts_to_database(
    db: Session,
    account_id: int,
    media_list: list
) -> None:
    """
    Save or update Instagram posts in database.

    Args:
        db: Database session
        account_id: Instagram account ID
        media_list: List of media items from Instagram API
    """
    for media in media_list:
        # Check if post already exists
        existing_post = db.query(InstagramPost).filter(
            InstagramPost.media_id == media["id"]
        ).first()

        # Extract insights
        insights = media.get("insights", [])
        likes_count = media.get("like_count", 0)
        comments_count = media.get("comments_count", 0)
        saves_count = 0
        shares_count = 0
        reach = 0
        impressions = 0

        for insight in insights:
            name = insight.get("name")
            value = insight.get("values", [{}])[0].get("value", 0)

            if name == "saved":
                saves_count = value
            elif name == "reach":
                reach = value
            elif name == "impressions":
                impressions = value

        # Calculate engagement rate
        engagement = likes_count + comments_count + saves_count
        engagement_rate = (engagement / reach * 100) if reach > 0 else 0

        if existing_post:
            # Update existing post
            existing_post.likes_count = likes_count
            existing_post.comments_count = comments_count
            existing_post.saves_count = saves_count
            existing_post.reach = reach
            existing_post.impressions = impressions
            existing_post.engagement_rate = engagement_rate
            existing_post.updated_at = datetime.utcnow()
        else:
            # Create new post
            new_post = InstagramPost(
                instagram_account_id=account_id,
                media_id=media["id"],
                media_type=media.get("media_type", "IMAGE"),
                media_url=media.get("media_url") or media.get("thumbnail_url"),
                permalink=media.get("permalink"),
                caption=media.get("caption"),
                timestamp=datetime.fromisoformat(media["timestamp"].replace("Z", "+00:00")),
                likes_count=likes_count,
                comments_count=comments_count,
                saves_count=saves_count,
                reach=reach,
                impressions=impressions,
                engagement_rate=engagement_rate
            )
            db.add(new_post)

    db.commit()
    logger.info(f"Saved {len(media_list)} posts to database")
