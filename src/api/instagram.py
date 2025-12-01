"""
Instagram OAuth and account management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from ..database import get_db
from ..database.models import InstagramAccount, User, InstagramPost
from .auth import get_current_active_user
from ..instagram.graph_api import get_instagram_api
from dateutil.parser import parse as parse_date

router = APIRouter()
logger = logging.getLogger(__name__)


class InstagramConnectRequest(BaseModel):
    authorization_code: str


class InstagramAccountResponse(BaseModel):
    id: int
    instagram_user_id: str
    username: str
    account_type: str
    followers_count: int
    is_active: bool
    last_synced_at: Optional[datetime]

    class Config:
        from_attributes = True


class InstagramAuthUrlResponse(BaseModel):
    authorization_url: str
    state: Optional[str] = None


@router.get("/auth-url", response_model=InstagramAuthUrlResponse)
async def get_instagram_auth_url(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get Instagram OAuth authorization URL.

    Returns URL for user to visit to authorize the app.
    """
    api = get_instagram_api()

    # Generate state for CSRF protection (could use user ID)
    state = f"user_{current_user.id}"

    auth_url = api.get_authorization_url(state=state)

    return {
        "authorization_url": auth_url,
        "state": state
    }


@router.post("/connect", response_model=InstagramAccountResponse)
async def connect_instagram(
    request: InstagramConnectRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Connect Instagram Business account using OAuth code.

    Flow:
    1. Exchange authorization code for short-lived token
    2. Exchange short-lived token for long-lived token (60 days)
    3. Fetch Instagram account info
    4. Save to database
    """
    api = get_instagram_api()

    try:
        # Step 1: Exchange code for short-lived token
        logger.info("Exchanging authorization code for access token")
        token_data = await api.exchange_code_for_token(request.authorization_code)
        short_lived_token = token_data["access_token"]

        # Step 2: Exchange for long-lived token
        logger.info("Exchanging for long-lived token")
        long_lived_data = await api.get_long_lived_token(short_lived_token)
        access_token = long_lived_data["access_token"]
        expires_in = long_lived_data.get("expires_in", 5184000)  # Default 60 days

        # Step 3: Fetch account info
        logger.info("Fetching Instagram account info")
        account_info = await api.get_account_info(access_token)

        # Verify it's a Business account
        if account_info.get("account_type") not in ["BUSINESS", "MEDIA_CREATOR"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only Instagram Business or Creator accounts are supported"
            )

        # Step 4: Check if account already exists
        existing_account = db.query(InstagramAccount).filter(
            InstagramAccount.instagram_user_id == account_info["id"]
        ).first()

        if existing_account:
            # Update existing account
            existing_account.username = account_info["username"]
            existing_account.account_type = account_info["account_type"]
            existing_account.access_token = access_token
            existing_account.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            existing_account.profile_picture_url = account_info.get("profile_picture_url")
            existing_account.followers_count = account_info.get("followers_count", 0)
            existing_account.media_count = account_info.get("media_count", 0)
            existing_account.is_active = True
            existing_account.updated_at = datetime.utcnow()

            # Update user association if needed
            if existing_account.user_id != current_user.id:
                logger.warning(
                    f"Instagram account {account_info['id']} was connected to user "
                    f"{existing_account.user_id}, now connecting to user {current_user.id}"
                )
                existing_account.user_id = current_user.id

            db.commit()
            db.refresh(existing_account)

            logger.info(f"Updated existing Instagram account: {account_info['username']}")
            return existing_account

        # Create new account
        new_account = InstagramAccount(
            user_id=current_user.id,
            instagram_user_id=account_info["id"],
            username=account_info["username"],
            account_type=account_info["account_type"],
            access_token=access_token,
            token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
            profile_picture_url=account_info.get("profile_picture_url"),
            followers_count=account_info.get("followers_count", 0),
            media_count=account_info.get("media_count", 0),
            is_active=True,
        )

        db.add(new_account)
        db.commit()
        db.refresh(new_account)

        logger.info(f"Connected new Instagram account: {account_info['username']}")
        return new_account

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to connect Instagram account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect Instagram account: {str(e)}"
        )


@router.get("/accounts", response_model=List[InstagramAccountResponse])
async def get_instagram_accounts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all Instagram accounts connected by the current user."""
    accounts = db.query(InstagramAccount).filter(
        InstagramAccount.user_id == current_user.id,
        InstagramAccount.is_active == True
    ).all()
    return accounts


@router.delete("/accounts/{account_id}")
async def disconnect_instagram(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Disconnect an Instagram account."""
    account = db.query(InstagramAccount).filter(
        InstagramAccount.id == account_id,
        InstagramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Instagram account not found")

    account.is_active = False
    db.commit()

    return {"message": "Instagram account disconnected successfully"}


# ========================================
# Content Publishing Endpoints
# ========================================

class PublishPhotoRequest(BaseModel):
    account_id: int
    image_url: str
    caption: Optional[str] = None


class PublishReelRequest(BaseModel):
    account_id: int
    video_url: str
    caption: Optional[str] = None
    cover_url: Optional[str] = None
    share_to_feed: bool = True


class PublishCarouselRequest(BaseModel):
    account_id: int
    media_urls: List[str]
    caption: Optional[str] = None


class PublishResponse(BaseModel):
    instagram_post_id: str
    status: str
    message: str


@router.post("/publish/photo", response_model=PublishResponse)
async def publish_photo(
    request: PublishPhotoRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Publish a photo to Instagram.

    Requirements:
    - Image must be publicly accessible URL
    - Min 320px, recommended 1080px
    - JPG or PNG format
    - Max 8MB file size
    """
    # Get and validate account
    account = db.query(InstagramAccount).filter(
        InstagramAccount.id == request.account_id,
        InstagramAccount.user_id == current_user.id,
        InstagramAccount.is_active == True
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Instagram account not found")

    # Check token expiration
    if account.token_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Instagram access token expired. Please reconnect your account."
        )

    try:
        api = get_instagram_api()
        result = await api.publish_photo(
            instagram_user_id=account.instagram_user_id,
            access_token=account.access_token,
            image_url=request.image_url,
            caption=request.caption,
            wait_for_completion=True
        )

        logger.info(f"Published photo to Instagram: {result.get('id')}")

        return PublishResponse(
            instagram_post_id=result["id"],
            status="published",
            message="Photo published successfully to Instagram"
        )

    except Exception as e:
        logger.error(f"Failed to publish photo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish photo: {str(e)}"
        )


@router.post("/publish/reel", response_model=PublishResponse)
async def publish_reel(
    request: PublishReelRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Publish a Reel to Instagram.

    Requirements:
    - Video must be publicly accessible URL
    - 3-90 seconds duration
    - 9:16 aspect ratio recommended
    - MP4 or MOV format
    - Max 100MB file size
    """
    account = db.query(InstagramAccount).filter(
        InstagramAccount.id == request.account_id,
        InstagramAccount.user_id == current_user.id,
        InstagramAccount.is_active == True
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Instagram account not found")

    if account.token_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Instagram access token expired. Please reconnect your account."
        )

    try:
        api = get_instagram_api()
        result = await api.publish_reel(
            instagram_user_id=account.instagram_user_id,
            access_token=account.access_token,
            video_url=request.video_url,
            caption=request.caption,
            cover_url=request.cover_url,
            share_to_feed=request.share_to_feed,
            wait_for_completion=True
        )

        logger.info(f"Published reel to Instagram: {result.get('id')}")

        return PublishResponse(
            instagram_post_id=result["id"],
            status="published",
            message="Reel published successfully to Instagram"
        )

    except Exception as e:
        logger.error(f"Failed to publish reel: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish reel: {str(e)}"
        )


@router.post("/publish/carousel", response_model=PublishResponse)
async def publish_carousel(
    request: PublishCarouselRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Publish a carousel (album) to Instagram.

    Requirements:
    - 2-10 items (images or videos)
    - All media must be publicly accessible URLs
    - Same requirements as photos/videos apply to each item
    """
    if len(request.media_urls) < 2 or len(request.media_urls) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Carousel must have 2-10 items"
        )

    account = db.query(InstagramAccount).filter(
        InstagramAccount.id == request.account_id,
        InstagramAccount.user_id == current_user.id,
        InstagramAccount.is_active == True
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Instagram account not found")

    if account.token_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Instagram access token expired. Please reconnect your account."
        )

    try:
        api = get_instagram_api()
        result = await api.publish_carousel(
            instagram_user_id=account.instagram_user_id,
            access_token=account.access_token,
            media_urls=request.media_urls,
            caption=request.caption,
            wait_for_completion=True
        )

        logger.info(f"Published carousel to Instagram: {result.get('id')}")

        return PublishResponse(
            instagram_post_id=result["id"],
            status="published",
            message="Carousel published successfully to Instagram"
        )

    except Exception as e:
        logger.error(f"Failed to publish carousel: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish carousel: {str(e)}"
        )


# ========================================
# Media Library Sync
# ========================================

class MediaSyncResponse(BaseModel):
    account_id: int
    username: str
    total_media_fetched: int
    new_posts: int
    updated_posts: int
    posts_with_insights: int
    oldest_post_date: Optional[datetime]
    newest_post_date: Optional[datetime]


@router.post("/sync-media/{account_id}", response_model=MediaSyncResponse)
async def sync_media_library(
    account_id: int,
    limit: Optional[int] = 100,
    force_refresh: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Sync all existing Instagram posts from the account.

    This fetches posts, media URLs, captions, and engagement metrics.
    Use this to build the media library for content repurposing.

    Args:
        account_id: Instagram account ID to sync
        limit: Max number of posts to fetch (default 100, max 200)
        force_refresh: Re-fetch posts even if already in database
    """
    account = db.query(InstagramAccount).filter(
        InstagramAccount.id == account_id,
        InstagramAccount.user_id == current_user.id,
        InstagramAccount.is_active == True
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Instagram account not found")

    if account.token_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Instagram access token expired. Please reconnect your account."
        )

    try:
        api = get_instagram_api()
        limit = min(limit, 200)  # Cap at 200

        logger.info(f"Starting media sync for account {account.username}")

        # Fetch media list
        media_response = await api.get_media_list(
            instagram_user_id=account.instagram_user_id,
            access_token=account.access_token,
            limit=limit
        )

        media_items = media_response.get("data", [])
        logger.info(f"Fetched {len(media_items)} media items")

        new_posts = 0
        updated_posts = 0
        posts_with_insights = 0
        oldest_date = None
        newest_date = None

        for media in media_items:
            media_id = media.get("id")

            # Check if post already exists
            existing_post = db.query(InstagramPost).filter(
                InstagramPost.media_id == media_id
            ).first()

            # Parse timestamp
            timestamp_str = media.get("timestamp")
            timestamp = parse_date(timestamp_str) if timestamp_str else datetime.utcnow()

            # Track date range
            if not oldest_date or timestamp < oldest_date:
                oldest_date = timestamp
            if not newest_date or timestamp > newest_date:
                newest_date = timestamp

            # Fetch insights for this media
            insights_data = {}
            try:
                insights_response = await api.get_media_insights(
                    media_id=media_id,
                    access_token=account.access_token
                )

                # Parse insights
                for insight in insights_response.get("data", []):
                    name = insight.get("name")
                    values = insight.get("values", [])
                    if values and len(values) > 0:
                        insights_data[name] = values[0].get("value", 0)

                posts_with_insights += 1
            except Exception as e:
                logger.warning(f"Failed to fetch insights for media {media_id}: {e}")

            # Calculate engagement rate
            likes = media.get("like_count", 0)
            comments = media.get("comments_count", 0)
            saves = insights_data.get("saved", 0)
            impressions = insights_data.get("impressions", 0)

            engagement_rate = 0.0
            if impressions > 0:
                engagement_rate = ((likes + comments + saves) / impressions) * 100

            if existing_post and not force_refresh:
                # Update existing post
                existing_post.likes_count = likes
                existing_post.comments_count = comments
                existing_post.saves_count = saves
                existing_post.shares_count = insights_data.get("shares", 0)
                existing_post.reach = insights_data.get("reach", 0)
                existing_post.impressions = impressions
                existing_post.engagement_rate = engagement_rate
                existing_post.caption = media.get("caption", "")
                existing_post.updated_at = datetime.utcnow()

                updated_posts += 1
            else:
                # Create new post
                new_post = InstagramPost(
                    instagram_account_id=account.id,
                    media_id=media_id,
                    media_type=media.get("media_type", "IMAGE"),
                    media_url=media.get("media_url") or media.get("thumbnail_url"),
                    permalink=media.get("permalink"),
                    caption=media.get("caption", ""),
                    timestamp=timestamp,
                    likes_count=likes,
                    comments_count=comments,
                    saves_count=saves,
                    shares_count=insights_data.get("shares", 0),
                    reach=insights_data.get("reach", 0),
                    impressions=impressions,
                    engagement_rate=engagement_rate,
                )
                db.add(new_post)
                new_posts += 1

        # Update account sync timestamp
        account.last_synced_at = datetime.utcnow()
        account.media_count = len(media_items)

        db.commit()

        logger.info(
            f"Media sync complete: {new_posts} new, {updated_posts} updated, "
            f"{posts_with_insights} with insights"
        )

        return MediaSyncResponse(
            account_id=account.id,
            username=account.username,
            total_media_fetched=len(media_items),
            new_posts=new_posts,
            updated_posts=updated_posts,
            posts_with_insights=posts_with_insights,
            oldest_post_date=oldest_date,
            newest_post_date=newest_date,
        )

    except Exception as e:
        logger.error(f"Failed to sync media library: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync media library: {str(e)}"
        )


@router.get("/media/{account_id}", response_model=List[dict])
async def get_media_library(
    account_id: int,
    media_type: Optional[str] = None,
    sort_by: str = "timestamp",
    order: str = "desc",
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get stored Instagram posts from the media library.

    Args:
        account_id: Instagram account ID
        media_type: Filter by type (IMAGE, VIDEO, CAROUSEL_ALBUM, REELS)
        sort_by: Sort field (timestamp, engagement_rate, likes_count, etc.)
        order: Sort order (asc, desc)
        limit: Max results (default 50)
    """
    account = db.query(InstagramAccount).filter(
        InstagramAccount.id == account_id,
        InstagramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Instagram account not found")

    query = db.query(InstagramPost).filter(
        InstagramPost.instagram_account_id == account_id
    )

    # Filter by media type
    if media_type:
        query = query.filter(InstagramPost.media_type == media_type)

    # Sort
    sort_column = getattr(InstagramPost, sort_by, InstagramPost.timestamp)
    if order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    posts = query.limit(limit).all()

    return [
        {
            "id": post.id,
            "media_id": post.media_id,
            "media_type": post.media_type,
            "media_url": post.media_url,
            "permalink": post.permalink,
            "caption": post.caption,
            "timestamp": post.timestamp,
            "likes_count": post.likes_count,
            "comments_count": post.comments_count,
            "saves_count": post.saves_count,
            "engagement_rate": post.engagement_rate,
            "impressions": post.impressions,
            "reach": post.reach,
        }
        for post in posts
    ]
