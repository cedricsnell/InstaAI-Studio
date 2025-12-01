"""
Content generation and management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ..database import get_db
from ..database.models import (
    GeneratedContent,
    ContentStatus,
    User,
    InstagramAccount,
    InstagramPost,
)
from .auth import get_current_active_user
from ..ai.content_repurposer import ContentRepurposer

router = APIRouter()
logger = logging.getLogger(__name__)


class ContentResponse(BaseModel):
    id: int
    content_type: str
    title: Optional[str]
    status: ContentStatus
    file_url: Optional[str]
    thumbnail_url: Optional[str]
    suggested_caption: Optional[str]
    predicted_engagement_rate: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[ContentResponse])
async def list_content(
    status: Optional[ContentStatus] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all generated content for the current user."""
    query = db.query(GeneratedContent).filter(
        GeneratedContent.user_id == current_user.id
    )

    if status:
        query = query.filter(GeneratedContent.status == status)

    content = query.order_by(GeneratedContent.created_at.desc()).all()
    return content


@router.post("/analyze-content/{account_id}")
async def analyze_content(
    account_id: int,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Analyze top-performing posts to identify content patterns and opportunities.

    Returns content themes, successful formats, caption patterns, and
    specific repurposing ideas.
    """
    # Verify account ownership
    account = db.query(InstagramAccount).filter(
        InstagramAccount.id == account_id,
        InstagramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Instagram account not found")

    # Fetch posts sorted by engagement
    posts = (
        db.query(InstagramPost)
        .filter(InstagramPost.instagram_account_id == account_id)
        .order_by(InstagramPost.engagement_rate.desc())
        .limit(limit)
        .all()
    )

    if not posts:
        raise HTTPException(
            status_code=400,
            detail="No posts found. Please sync your media library first using /instagram/sync-media"
        )

    # Convert to dict format
    posts_data = [
        {
            "media_id": p.media_id,
            "media_type": p.media_type,
            "caption": p.caption,
            "engagement_rate": p.engagement_rate,
            "likes_count": p.likes_count,
            "comments_count": p.comments_count,
            "saves_count": p.saves_count,
            "timestamp": p.timestamp,
            "media_url": p.media_url,
        }
        for p in posts
    ]

    account_context = {
        "niche": "General",  # TODO: Add niche to account model
        "followers_count": account.followers_count,
        "account_type": account.account_type,
    }

    try:
        repurposer = ContentRepurposer()
        analysis = repurposer.analyze_top_performing_posts(posts_data, account_context)

        logger.info(f"Content analysis complete for account {account.username}")
        return {
            "account_id": account_id,
            "username": account.username,
            "posts_analyzed": len(posts),
            "analysis": analysis,
            "analyzed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Content analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content analysis failed: {str(e)}"
        )


@router.post("/generate-reels/{account_id}")
async def generate_reel_ideas(
    account_id: int,
    count: int = 10,
    niche: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate AI-powered reel ideas based on your top-performing content.

    Returns detailed reel concepts including scripts, hooks, visual plans,
    and production notes.

    Args:
        account_id: Instagram account ID
        count: Number of reel ideas to generate (1-20)
        niche: Optional niche/industry for better targeting
    """
    count = max(1, min(20, count))  # Cap between 1-20

    account = db.query(InstagramAccount).filter(
        InstagramAccount.id == account_id,
        InstagramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Instagram account not found")

    # Fetch all posts
    posts = (
        db.query(InstagramPost)
        .filter(InstagramPost.instagram_account_id == account_id)
        .order_by(InstagramPost.engagement_rate.desc())
        .limit(100)
        .all()
    )

    if not posts:
        raise HTTPException(
            status_code=400,
            detail="No posts found. Please sync your media library first"
        )

    posts_data = [
        {
            "id": p.id,
            "media_id": p.media_id,
            "media_type": p.media_type,
            "caption": p.caption,
            "engagement_rate": p.engagement_rate,
            "likes_count": p.likes_count,
            "media_url": p.media_url,
        }
        for p in posts
    ]

    try:
        repurposer = ContentRepurposer()

        # First analyze content
        analysis = repurposer.analyze_top_performing_posts(
            posts_data[:20], {"niche": niche or "General"}
        )

        # Generate reel ideas
        reel_ideas = repurposer.generate_reel_ideas(
            source_posts=posts_data, analysis=analysis, count=count, niche=niche
        )

        # Save as generated content
        saved_reels = []
        for reel in reel_ideas:
            content = GeneratedContent(
                user_id=current_user.id,
                instagram_account_id=account_id,
                content_type="reel",
                title=reel.get("title", "Untitled Reel"),
                description=reel.get("script", ""),
                suggested_caption=reel.get("caption", ""),
                generation_config=reel,  # Store full reel plan
                status=ContentStatus.READY,
            )
            db.add(content)
            saved_reels.append(content)

        db.commit()

        logger.info(f"Generated {len(reel_ideas)} reel ideas for {account.username}")

        return {
            "account_id": account_id,
            "username": account.username,
            "reel_count": len(reel_ideas),
            "reels": reel_ideas,
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Reel generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reel generation failed: {str(e)}"
        )


@router.post("/generate-carousel/{account_id}")
async def generate_carousel_idea(
    account_id: int,
    theme: str,
    slide_count: int = 7,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate a carousel post concept on a specific theme.

    Args:
        account_id: Instagram account ID
        theme: Main theme/topic for the carousel
        slide_count: Number of slides (2-10)
    """
    slide_count = max(2, min(10, slide_count))

    account = db.query(InstagramAccount).filter(
        InstagramAccount.id == account_id,
        InstagramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Instagram account not found")

    # Fetch posts
    posts = (
        db.query(InstagramPost)
        .filter(InstagramPost.instagram_account_id == account_id)
        .limit(50)
        .all()
    )

    if not posts:
        raise HTTPException(status_code=400, detail="No posts found. Sync media first")

    posts_data = [
        {
            "id": p.id,
            "caption": p.caption,
            "media_type": p.media_type,
            "engagement_rate": p.engagement_rate,
        }
        for p in posts
    ]

    try:
        repurposer = ContentRepurposer()
        carousel = repurposer.generate_carousel_from_content(
            theme=theme, source_posts=posts_data, slide_count=slide_count
        )

        # Save as generated content
        content = GeneratedContent(
            user_id=current_user.id,
            instagram_account_id=account_id,
            content_type="carousel",
            title=carousel.get("title", theme),
            description=f"{slide_count}-slide carousel about {theme}",
            suggested_caption=carousel.get("caption", ""),
            generation_config=carousel,
            status=ContentStatus.READY,
        )
        db.add(content)
        db.commit()

        logger.info(f"Generated carousel concept: {theme}")

        return {
            "account_id": account_id,
            "carousel": carousel,
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Carousel generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Carousel generation failed: {str(e)}"
        )


@router.patch("/{content_id}/approve")
async def approve_content(
    content_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Approve generated content for publishing."""
    content = db.query(GeneratedContent).filter(
        GeneratedContent.id == content_id,
        GeneratedContent.user_id == current_user.id
    ).first()

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    content.status = ContentStatus.APPROVED
    content.approved_at = datetime.utcnow()
    db.commit()

    return {"message": "Content approved", "content_id": content_id}


@router.delete("/{content_id}")
async def delete_content(
    content_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete generated content."""
    content = db.query(GeneratedContent).filter(
        GeneratedContent.id == content_id,
        GeneratedContent.user_id == current_user.id
    ).first()

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    db.delete(content)
    db.commit()

    return {"message": "Content deleted successfully"}
