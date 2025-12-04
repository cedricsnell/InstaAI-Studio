"""
Database models for InstaAI backend.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, JSON,
    Float, ForeignKey, Text, Enum as SQLEnum, Index
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
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth-only users
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # OAuth fields
    google_id = Column(String(255), unique=True, nullable=True)
    google_email = Column(String(255), nullable=True)
    facebook_id = Column(String(255), unique=True, nullable=True)
    oauth_provider = Column(String(50), nullable=True)  # google, facebook, apple
    oauth_id = Column(String(255), nullable=True)  # Universal OAuth ID field

    # Subscription & billing
    subscription_tier = Column(String(50), default='free')  # free, starter, pro, agency
    subscription_status = Column(String(50), default='active')  # active, canceled, expired
    subscription_expires_at = Column(DateTime, nullable=True)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)

    # Usage tracking
    content_generated_count = Column(Integer, default=0)
    posts_scheduled_count = Column(Integer, default=0)
    monthly_quota_remaining = Column(Integer, default=10)
    quota_reset_date = Column(DateTime, nullable=True)

    # Preferences
    timezone = Column(String(100), default='UTC')
    language = Column(String(10), default='en')
    onboarding_completed = Column(Boolean, default=False)
    email_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=True)

    # Security
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime, nullable=True)

    # Relationships
    instagram_accounts = relationship("InstagramAccount", back_populates="user", cascade="all, delete-orphan")
    generated_content = relationship("GeneratedContent", back_populates="user", cascade="all, delete-orphan")


class InstagramAccount(Base):
    """Instagram accounts connected by users or teams."""
    __tablename__ = "instagram_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)  # Optional team ownership

    # Instagram Business Account Info
    instagram_user_id = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=False, index=True)
    account_type = Column(String(50))  # BUSINESS, MEDIA_CREATOR, PERSONAL

    # OAuth tokens (should be encrypted in production)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=False)

    # Account metadata
    profile_picture_url = Column(Text, nullable=True)
    followers_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    media_count = Column(Integer, default=0)
    biography = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    last_synced_at = Column(DateTime, nullable=True)
    sync_error = Column(Text, nullable=True)
    next_sync_at = Column(DateTime, nullable=True, index=True)
    sync_frequency_hours = Column(Integer, default=6)  # Sync every 6 hours

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
    instagram_account_id = Column(Integer, ForeignKey("instagram_accounts.id"), nullable=False, index=True)

    # Post data from Instagram
    media_id = Column(String(255), unique=True, nullable=False, index=True)
    media_type = Column(String(50))  # IMAGE, VIDEO, CAROUSEL_ALBUM, REELS
    media_url = Column(Text)
    thumbnail_url = Column(Text)
    permalink = Column(Text)
    caption = Column(Text)
    timestamp = Column(DateTime, nullable=False, index=True)

    # Engagement metrics (updated periodically)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    saves_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0, index=True)
    plays = Column(Integer, default=0)  # For videos/reels

    # AI Analysis
    ai_tags = Column(JSON, nullable=True)  # ["fitness", "workout", "gym"]
    ai_sentiment = Column(String(50), nullable=True)  # positive, neutral, negative
    ai_content_themes = Column(JSON, nullable=True)  # ["motivation", "tutorial"]
    performance_score = Column(Float, nullable=True)  # 0-100 score based on engagement

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_metrics_update = Column(DateTime, nullable=True)

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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    instagram_account_id = Column(Integer, ForeignKey("instagram_accounts.id"), nullable=True, index=True)

    # Content metadata
    content_type = Column(String(50), index=True)  # reel, story, carousel, image
    title = Column(String(500))
    description = Column(Text)

    # Cloud Storage (Cloudflare R2 / Supabase Storage)
    file_url = Column(Text, nullable=True)  # Public CDN URL
    thumbnail_url = Column(Text, nullable=True)
    storage_key = Column(Text, nullable=True)  # R2 object key or Supabase path
    storage_provider = Column(String(50), default='r2')  # r2, supabase, cloudinary
    file_size_bytes = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # For videos

    # AI generation details
    source_post_ids = Column(JSON, nullable=True)  # List of InstagramPost IDs used
    ai_prompt = Column(Text, nullable=True)
    ai_model = Column(String(100), nullable=True)  # gpt-4, claude-3-opus, etc
    generation_config = Column(JSON, nullable=True)  # Full config used
    processing_time_seconds = Column(Integer, nullable=True)

    # Content recommendations
    suggested_caption = Column(Text, nullable=True)
    suggested_hashtags = Column(JSON, nullable=True)  # ["fitness", "workout"]
    best_posting_time = Column(DateTime, nullable=True)
    target_audience = Column(String(100), nullable=True)  # "fitness enthusiasts"

    # Status
    status = Column(SQLEnum(ContentStatus), default=ContentStatus.PENDING, index=True)
    status_message = Column(Text, nullable=True)

    # Performance prediction
    predicted_engagement_rate = Column(Float, nullable=True)
    predicted_reach = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)  # 0.0-1.0

    # Actual performance (filled after publishing)
    actual_engagement_rate = Column(Float, nullable=True)
    actual_reach = Column(Integer, nullable=True)
    published_post_id = Column(Integer, ForeignKey("instagram_posts.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
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
    instagram_account_id = Column(Integer, ForeignKey("instagram_accounts.id"), nullable=False, index=True)
    generated_content_id = Column(Integer, ForeignKey("generated_content.id"), nullable=True)

    # Schedule details
    scheduled_time = Column(DateTime, nullable=False, index=True)
    timezone = Column(String(100), default='UTC')
    post_type = Column(String(50))  # reel, story, carousel, photo

    # Content
    media_url = Column(Text, nullable=True)
    caption = Column(Text)
    hashtags = Column(JSON, nullable=True)  # ["fitness", "workout"]
    location_id = Column(String(255), nullable=True)
    collaborators = Column(JSON, nullable=True)  # User IDs to tag

    # Status
    status = Column(SQLEnum(ScheduleStatus), default=ScheduleStatus.SCHEDULED, index=True)
    status_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Result
    instagram_post_id = Column(String(255), nullable=True)  # ID from Instagram after posting
    posted_at = Column(DateTime, nullable=True)
    error_log = Column(JSON, nullable=True)  # Array of error messages

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    instagram_account = relationship("InstagramAccount", back_populates="post_schedule")


# New Enterprise Tables

class AnalyticsCache(Base):
    """Cache for aggregated analytics data to reduce Instagram API calls."""
    __tablename__ = "analytics_cache"

    id = Column(Integer, primary_key=True, index=True)
    instagram_account_id = Column(Integer, ForeignKey("instagram_accounts.id"), nullable=False)

    # Cache metadata
    metric_type = Column(String(100), nullable=False)  # engagement, reach, followers, etc
    metric_period = Column(String(50), nullable=False)  # daily, weekly, monthly
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Cached data (JSON)
    data = Column(JSON, nullable=False)

    # Cache control
    cached_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)

    # Index for fast lookups
    __table_args__ = (
        Index('idx_analytics_lookup', 'instagram_account_id', 'metric_type', 'metric_period'),
    )


class APIRateLimit(Base):
    """Track Instagram API rate limits per account and endpoint."""
    __tablename__ = "api_rate_limits"

    id = Column(Integer, primary_key=True, index=True)
    instagram_account_id = Column(Integer, ForeignKey("instagram_accounts.id"), nullable=False)

    # Rate limit tracking
    endpoint = Column(String(255), nullable=False)  # /insights, /media, etc
    requests_count = Column(Integer, default=0)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)

    # Limit configuration (from Instagram)
    rate_limit = Column(Integer, default=200)  # Requests per window
    window_duration_seconds = Column(Integer, default=3600)  # 1 hour

    # Status
    is_throttled = Column(Boolean, default=False)
    throttle_until = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_rate_limit_lookup', 'instagram_account_id', 'endpoint', 'window_start'),
    )


class AuditLog(Base):
    """Security audit log for tracking all important user actions."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Action details
    action = Column(String(100), nullable=False, index=True)  # login, post_scheduled, content_generated
    resource_type = Column(String(100), nullable=True)  # user, instagram_account, post
    resource_id = Column(Integer, nullable=True)

    # Change tracking
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)

    # Request metadata
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    request_path = Column(String(500), nullable=True)

    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class WebhookLog(Base):
    """Log all webhook events from Instagram for debugging."""
    __tablename__ = "webhook_logs"

    id = Column(Integer, primary_key=True, index=True)
    instagram_account_id = Column(Integer, ForeignKey("instagram_accounts.id"), nullable=True)

    # Webhook details
    event_type = Column(String(100), nullable=False)  # media, comments, mentions
    payload = Column(JSON, nullable=False)

    # Processing
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    received_at = Column(DateTime, default=datetime.utcnow, index=True)


class ContentTemplate(Base):
    """Reusable content templates for faster generation."""
    __tablename__ = "content_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Template metadata
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # workout, recipe, tutorial, etc

    # Template structure
    content_type = Column(String(50))  # reel, carousel, story
    prompt_template = Column(Text, nullable=False)  # AI prompt with placeholders
    caption_template = Column(Text)
    default_hashtags = Column(JSON)

    # Usage stats
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)

    # Sharing
    is_public = Column(Boolean, default=False)
    created_by_verified = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ========================================
# Team/Agency Management Models
# ========================================

class TeamRole(str, enum.Enum):
    """Roles for team members."""
    OWNER = "owner"           # Full control, can delete team
    ADMIN = "admin"           # Can manage members and settings
    MEMBER = "member"         # Can view and edit content
    VIEWER = "viewer"         # Read-only access


class InviteStatus(str, enum.Enum):
    """Status of team invitations."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class Team(Base):
    """Teams/Workspaces for agencies managing multiple clients."""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Owner/creator
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Team settings
    is_active = Column(Boolean, default=True)
    max_members = Column(Integer, default=10)  # Subscription-based limit
    
    # Billing (if team has its own subscription)
    subscription_tier = Column(String(50), default='free')
    stripe_customer_id = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    invites = relationship("TeamInvite", back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    """Membership linking users to teams with roles."""
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    role = Column(SQLEnum(TeamRole), default=TeamRole.MEMBER, nullable=False)
    
    # Permissions
    can_manage_content = Column(Boolean, default=True)
    can_manage_instagram = Column(Boolean, default=True)
    can_view_analytics = Column(Boolean, default=True)
    can_invite_members = Column(Boolean, default=False)
    
    joined_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User")
    
    # Unique constraint: user can only be in a team once
    __table_args__ = (
        Index('idx_team_user', 'team_id', 'user_id', unique=True),
    )


class TeamInvite(Base):
    """Pending invitations to join teams."""
    __tablename__ = "team_invites"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    
    # Invite details
    email = Column(String(255), nullable=False, index=True)
    role = Column(SQLEnum(TeamRole), default=TeamRole.MEMBER, nullable=False)
    
    # Who sent the invite
    invited_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Status tracking
    status = Column(SQLEnum(InviteStatus), default=InviteStatus.PENDING, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)  # Unique invite token
    
    # Permissions for this invite
    can_manage_content = Column(Boolean, default=True)
    can_manage_instagram = Column(Boolean, default=True)
    can_view_analytics = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)  # Invites expire after X days
    accepted_at = Column(DateTime, nullable=True)
    
    # Relationships
    team = relationship("Team", back_populates="invites")
    invited_by = relationship("User", foreign_keys=[invited_by_id])


# Update InstagramAccount to support team access
# Add team_id column (migration will handle this)
