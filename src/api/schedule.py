"""
Post scheduling endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..database.models import PostSchedule, ScheduleStatus, User, GeneratedContent, InstagramAccount
from .auth import get_current_active_user

router = APIRouter()


class ScheduleCreateRequest(BaseModel):
    content_id: int
    account_id: int
    scheduled_time: datetime
    caption: Optional[str] = None


class ScheduleResponse(BaseModel):
    id: int
    scheduled_time: datetime
    post_type: str
    status: ScheduleStatus
    caption: Optional[str]
    instagram_post_id: Optional[str]
    posted_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[ScheduleResponse])
async def list_scheduled_posts(
    account_id: int,
    status: Optional[ScheduleStatus] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all scheduled posts for an account."""
    query = db.query(PostSchedule).filter(
        PostSchedule.instagram_account_id == account_id
    )

    if status:
        query = query.filter(PostSchedule.status == status)

    posts = query.order_by(PostSchedule.scheduled_time.asc()).all()
    return posts


@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def schedule_post(
    request: ScheduleCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Schedule a piece of generated content for future publishing."""
    # Validate content exists and belongs to user
    content = db.query(GeneratedContent).filter(
        GeneratedContent.id == request.content_id,
        GeneratedContent.user_id == current_user.id
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # Validate account exists and belongs to user
    account = db.query(InstagramAccount).filter(
        InstagramAccount.id == request.account_id,
        InstagramAccount.user_id == current_user.id,
        InstagramAccount.is_active == True
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Instagram account not found")

    if request.scheduled_time <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Scheduled time must be in the future")

    post = PostSchedule(
        instagram_account_id=request.account_id,
        generated_content_id=request.content_id,
        scheduled_time=request.scheduled_time,
        post_type=content.content_type or "reel",
        media_url=content.file_url,
        caption=request.caption or content.suggested_caption,
        status=ScheduleStatus.SCHEDULED,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.delete("/{schedule_id}")
async def cancel_scheduled_post(
    schedule_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel a scheduled post."""
    post = db.query(PostSchedule).filter(
        PostSchedule.id == schedule_id
    ).first()

    if not post:
        raise HTTPException(status_code=404, detail="Scheduled post not found")

    if post.status == ScheduleStatus.PUBLISHED:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel already published post"
        )

    post.status = ScheduleStatus.CANCELLED
    db.commit()

    return {"message": "Scheduled post cancelled successfully"}
