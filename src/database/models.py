"""
Database models for InstaAI backend.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, JSON,
    Float, ForeignKey, Text, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class User(Base):
    """User accounts table."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # OAuth fields
    google_id = Column(String(255), unique=True, nullable=True)
    google_email = Column(String(255), nullable=True)
    oauth_provider = Column(String(50), nullable=True)  # google, facebook, apple
    oauth_id = Column(String(255), nullable=True)  # Universal OAuth ID field

    # Subscription
    subscription_tier = Column(String(50), default='free')  # free, starter, pro, agency
    subscription_expires = Column(DateTime, nullable=True)

    # Relationships
    instagram_accounts = relationship("InstagramAccount", back_populates="user", cascade="all, delete-orphan")
    generated_content = relationship("GeneratedContent", back_populates="user", cascade="all, delete-orphan")


class InstagramAccount(Base):
    """Instagram accounts connected by users."""
    __tablename__ = "instagram_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Instagram Business Account Info
    instagram_user_id = Column(String(255), unique=True, nullable=False)
    username = Column(String(255), nullable=False)
    account_type = Column(String(50))  # BUSINESS, MEDIA_CREATOR, PERSONAL

    # OAuth tokens
    access_token = Column(Text, nullable=False)
    token_expires_at = Column(DateTime, nullable=False)

    # Account metadata
    profile_picture_url = Column(Text, nullable=True)
    followers_count = Column(Integer, default=0)
    media_count = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="instagram_accounts")
    insights_cache = relationship("InsightsCache", back_populates="instagram_account", cascade="all, delete-orphan")
    posts = relationship("InstagramPost", back_populates="instagram_account", cascade="all, delete-orphan")
    post_schedule = relationship("PostSchedule", back_populates="instagram_account", cascade="all, delete-orphan")


class InsightsCache(Base):
    """Cached Instagram insights data."""
    __tablename__ = "insights_cache"

    id = Column(Integer, primary_key=True, index=True)
    instagram_account_id = Column(Integer, ForeignKey("instagram_accounts.id"), nullable=False)

    # Cached data
    insights_data = Column(JSON, nullable=False)  # Full insights JSON
    ai_recommendations = Column(JSON, nullable=True)  # AI-generated recommendations

    # Cache metadata
    cached_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    # Relationships
    instagram_account = relationship("InstagramAccount", back_populates="insights_cache")


class InstagramPost(Base):
    """Instagram posts fetched from API."""
    __tablename__ = "instagram_posts"

    id = Column(Integer, primary_key=True, index=True)
    instagram_account_id = Column(Integer, ForeignKey("instagram_accounts.id"), nullable=False)

    # Post data from Instagram
    media_id = Column(String(255), unique=True, nullable=False)
    media_type = Column(String(50))  # IMAGE, VIDEO, CAROUSEL_ALBUM, REELS
    media_url = Column(Text)
    permalink = Column(Text)
    caption = Column(Text)
    timestamp = Column(DateTime, nullable=False)

    # Engagement metrics
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    saves_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    instagram_account = relationship("InstagramAccount", back_populates="posts")


class ContentStatus(str, enum.Enum):
    """Status of generated content."""
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    FAILED = "failed"


class GeneratedContent(Base):
    """AI-generated content for Instagram."""
    __tablename__ = "generated_content"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    instagram_account_id = Column(Integer, ForeignKey("instagram_accounts.id"), nullable=True)

    # Content metadata
    content_type = Column(String(50))  # reel, story, carousel, image
    title = Column(String(500))
    description = Column(Text)

    # Generated files
    file_url = Column(Text, nullable=True)  # S3/Cloudinary URL
    thumbnail_url = Column(Text, nullable=True)
    local_path = Column(Text, nullable=True)  # Local file path

    # AI generation details
    source_clips = Column(JSON, nullable=True)  # List of source media IDs used
    ai_prompt = Column(Text, nullable=True)
    generation_config = Column(JSON, nullable=True)  # Parameters used for generation

    # Caption and metadata
    suggested_caption = Column(Text, nullable=True)
    suggested_hashtags = Column(JSON, nullable=True)  # Array of hashtags
    best_posting_time = Column(DateTime, nullable=True)

    # Status
    status = Column(SQLEnum(ContentStatus), default=ContentStatus.PENDING)
    status_message = Column(Text, nullable=True)

    # Performance prediction
    predicted_engagement_rate = Column(Float, nullable=True)
    predicted_reach = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="generated_content")


class ScheduleStatus(str, enum.Enum):
    """Status of scheduled posts."""
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PostSchedule(Base):
    """Scheduled Instagram posts."""
    __tablename__ = "post_schedule"

    id = Column(Integer, primary_key=True, index=True)
    instagram_account_id = Column(Integer, ForeignKey("instagram_accounts.id"), nullable=False)
    generated_content_id = Column(Integer, ForeignKey("generated_content.id"), nullable=True)

    # Schedule details
    scheduled_time = Column(DateTime, nullable=False, index=True)
    post_type = Column(String(50))  # reel, story, carousel, photo

    # Content
    media_path = Column(Text, nullable=True)
    media_url = Column(Text, nullable=True)
    caption = Column(Text)
    hashtags = Column(JSON, nullable=True)  # Array of hashtags

    # Status
    status = Column(SQLEnum(ScheduleStatus), default=ScheduleStatus.SCHEDULED)
    status_message = Column(Text, nullable=True)

    # Result
    instagram_post_id = Column(String(255), nullable=True)  # ID from Instagram after posting
    posted_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    instagram_account = relationship("InstagramAccount", back_populates="post_schedule")
