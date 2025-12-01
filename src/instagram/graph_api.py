"""
Instagram Graph API client for Business accounts.
Handles OAuth, insights, posts, and audience data.
"""
import os
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Instagram Graph API endpoints
GRAPH_API_BASE = "https://graph.facebook.com/v18.0"
OAUTH_BASE = "https://api.instagram.com"


class InstagramGraphAPI:
    """Client for Instagram Graph API (Business accounts only)."""

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None
    ):
        """
        Initialize Instagram Graph API client.

        Args:
            app_id: Instagram/Facebook App ID
            app_secret: Instagram/Facebook App Secret
            redirect_uri: OAuth redirect URI
        """
        self.app_id = app_id or os.getenv("INSTAGRAM_APP_ID")
        self.app_secret = app_secret or os.getenv("INSTAGRAM_APP_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("INSTAGRAM_REDIRECT_URI")

        if not all([self.app_id, self.app_secret, self.redirect_uri]):
            logger.warning(
                "Instagram credentials not fully configured. "
                "Set INSTAGRAM_APP_ID, INSTAGRAM_APP_SECRET, and INSTAGRAM_REDIRECT_URI"
            )

    # ========================================
    # OAuth Flow
    # ========================================

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Get Instagram OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL for user to visit
        """
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "scope": "instagram_basic,instagram_manage_insights,pages_read_engagement",
            "response_type": "code",
        }
        if state:
            params["state"] = state

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{OAUTH_BASE}/oauth/authorize?{query_string}"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for short-lived access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            {
                "access_token": "...",
                "user_id": "...",
                "expires_in": 3600
            }
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OAUTH_BASE}/oauth/access_token",
                data={
                    "client_id": self.app_id,
                    "client_secret": self.app_secret,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                    "code": code,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_long_lived_token(self, short_lived_token: str) -> Dict[str, Any]:
        """
        Exchange short-lived token for long-lived token (60 days).

        Args:
            short_lived_token: Short-lived access token

        Returns:
            {
                "access_token": "...",
                "token_type": "bearer",
                "expires_in": 5183944  # ~60 days
            }
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GRAPH_API_BASE}/access_token",
                params={
                    "grant_type": "ig_exchange_token",
                    "client_secret": self.app_secret,
                    "access_token": short_lived_token,
                },
            )
            response.raise_for_status()
            return response.json()

    async def refresh_long_lived_token(self, access_token: str) -> Dict[str, Any]:
        """
        Refresh a long-lived token (extends by 60 days).

        Args:
            access_token: Current long-lived token

        Returns:
            {
                "access_token": "...",
                "token_type": "bearer",
                "expires_in": 5183944
            }
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GRAPH_API_BASE}/refresh_access_token",
                params={
                    "grant_type": "ig_refresh_token",
                    "access_token": access_token,
                },
            )
            response.raise_for_status()
            return response.json()

    # ========================================
    # Account Information
    # ========================================

    async def get_account_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get Instagram Business account information.

        Args:
            access_token: Long-lived access token

        Returns:
            {
                "id": "instagram_user_id",
                "username": "username",
                "account_type": "BUSINESS",
                "media_count": 100,
                "followers_count": 5000,
                "follows_count": 250,
                "profile_picture_url": "https://..."
            }
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GRAPH_API_BASE}/me",
                params={
                    "fields": "id,username,account_type,media_count,followers_count,follows_count,profile_picture_url",
                    "access_token": access_token,
                },
            )
            response.raise_for_status()
            return response.json()

    # ========================================
    # Insights (Analytics)
    # ========================================

    async def get_account_insights(
        self,
        instagram_user_id: str,
        access_token: str,
        period: str = "day",
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get account-level insights.

        Args:
            instagram_user_id: Instagram Business Account ID
            access_token: Access token
            period: Time period - 'day', 'week', 'days_28', or 'lifetime'
            since: Start date (default: 30 days ago)
            until: End date (default: today)

        Returns:
            {
                "data": [
                    {
                        "name": "impressions",
                        "period": "day",
                        "values": [{"value": 1234, "end_time": "..."}],
                        "title": "Impressions",
                        "description": "Total impressions"
                    },
                    ...
                ]
            }

        Available metrics:
        - impressions: Total impressions
        - reach: Total reach
        - follower_count: Follower count
        - email_contacts: Email button taps
        - phone_call_clicks: Call button taps
        - text_message_clicks: Text button taps
        - get_directions_clicks: Directions button taps
        - website_clicks: Website button taps
        - profile_views: Profile views
        """
        if not since:
            since = datetime.utcnow() - timedelta(days=30)
        if not until:
            until = datetime.utcnow()

        metrics = [
            "impressions",
            "reach",
            "follower_count",
            "email_contacts",
            "phone_call_clicks",
            "text_message_clicks",
            "get_directions_clicks",
            "website_clicks",
            "profile_views",
        ]

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GRAPH_API_BASE}/{instagram_user_id}/insights",
                params={
                    "metric": ",".join(metrics),
                    "period": period,
                    "since": int(since.timestamp()),
                    "until": int(until.timestamp()),
                    "access_token": access_token,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_media_list(
        self,
        instagram_user_id: str,
        access_token: str,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Get list of media (posts) for the account.

        Args:
            instagram_user_id: Instagram Business Account ID
            access_token: Access token
            limit: Number of media items to fetch (max 100)

        Returns:
            {
                "data": [
                    {
                        "id": "media_id",
                        "media_type": "IMAGE",
                        "media_url": "https://...",
                        "permalink": "https://instagram.com/p/...",
                        "caption": "Post caption",
                        "timestamp": "2024-11-29T12:00:00+0000",
                        "like_count": 100,
                        "comments_count": 10
                    },
                    ...
                ],
                "paging": {...}
            }
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GRAPH_API_BASE}/{instagram_user_id}/media",
                params={
                    "fields": "id,media_type,media_url,permalink,caption,timestamp,like_count,comments_count,thumbnail_url",
                    "limit": min(limit, 100),
                    "access_token": access_token,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_media_insights(
        self,
        media_id: str,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Get insights for a specific media item.

        Args:
            media_id: Instagram media ID
            access_token: Access token

        Returns:
            {
                "data": [
                    {
                        "name": "impressions",
                        "period": "lifetime",
                        "values": [{"value": 1234}],
                        "title": "Impressions"
                    },
                    ...
                ]
            }

        Available metrics (depends on media type):
        - engagement: Total engagement (likes + comments + saves)
        - impressions: Total impressions
        - reach: Total reach
        - saved: Total saves
        - video_views: Video views (VIDEO only)
        - likes: Total likes
        - comments: Total comments
        - shares: Total shares
        """
        # Determine metrics based on media type
        # For simplicity, request all available metrics
        metrics = [
            "engagement",
            "impressions",
            "reach",
            "saved",
            "video_views",  # Only for videos
        ]

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GRAPH_API_BASE}/{media_id}/insights",
                params={
                    "metric": ",".join(metrics),
                    "access_token": access_token,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_audience_insights(
        self,
        instagram_user_id: str,
        access_token: str,
        period: str = "lifetime",
    ) -> Dict[str, Any]:
        """
        Get audience demographic insights.

        Args:
            instagram_user_id: Instagram Business Account ID
            access_token: Access token
            period: 'lifetime' or 'days_28'

        Returns:
            {
                "data": [
                    {
                        "name": "audience_gender_age",
                        "period": "lifetime",
                        "values": [{
                            "value": {
                                "M.25-34": 50,
                                "F.25-34": 30,
                                ...
                            }
                        }]
                    },
                    {
                        "name": "audience_city",
                        "values": [{
                            "value": {
                                "New York, NY": 100,
                                "Los Angeles, CA": 80,
                                ...
                            }
                        }]
                    },
                    ...
                ]
            }

        Available metrics:
        - audience_gender_age: Gender and age breakdown
        - audience_locale: Top languages
        - audience_country: Top countries
        - audience_city: Top cities
        - online_followers: When followers are online
        """
        metrics = [
            "audience_gender_age",
            "audience_locale",
            "audience_country",
            "audience_city",
            "online_followers",
        ]

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GRAPH_API_BASE}/{instagram_user_id}/insights",
                params={
                    "metric": ",".join(metrics),
                    "period": period,
                    "access_token": access_token,
                },
            )
            response.raise_for_status()
            return response.json()

    # ========================================
    # Content Publishing (Instagram Graph API)
    # ========================================

    async def create_media_container(
        self,
        instagram_user_id: str,
        access_token: str,
        image_url: Optional[str] = None,
        video_url: Optional[str] = None,
        caption: Optional[str] = None,
        is_carousel_item: bool = False,
        cover_url: Optional[str] = None,
        location_id: Optional[str] = None,
        user_tags: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Create a media container (Step 1 of publishing).

        Args:
            instagram_user_id: Instagram Business Account ID
            access_token: Access token
            image_url: Publicly accessible image URL
            video_url: Publicly accessible video URL
            caption: Post caption (max 2200 chars)
            is_carousel_item: True if this is part of a carousel
            cover_url: Cover image for video (optional)
            location_id: Location ID from Facebook Places
            user_tags: List of tagged users

        Returns:
            Container ID (use this to publish)

        Note:
            Media URLs must be publicly accessible.
            Videos: Max 100MB, up to 60 minutes
            Images: Max 8MB, min 320px
        """
        if not image_url and not video_url:
            raise ValueError("Either image_url or video_url must be provided")

        params = {
            "access_token": access_token,
        }

        # Add media URL
        if image_url:
            params["image_url"] = image_url
        if video_url:
            params["video_url"] = video_url
            params["media_type"] = "VIDEO"
            if cover_url:
                params["cover_url"] = cover_url

        # Add optional params
        if caption and not is_carousel_item:
            params["caption"] = caption[:2200]  # Max length
        if location_id:
            params["location_id"] = location_id
        if user_tags:
            params["user_tags"] = user_tags
        if is_carousel_item:
            params["is_carousel_item"] = "true"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{GRAPH_API_BASE}/{instagram_user_id}/media",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            return data["id"]

    async def create_carousel_container(
        self,
        instagram_user_id: str,
        access_token: str,
        children: List[str],
        caption: Optional[str] = None,
    ) -> str:
        """
        Create a carousel album container.

        Args:
            instagram_user_id: Instagram Business Account ID
            access_token: Access token
            children: List of container IDs (2-10 items)
            caption: Album caption

        Returns:
            Carousel container ID
        """
        if len(children) < 2 or len(children) > 10:
            raise ValueError("Carousel must have 2-10 items")

        params = {
            "access_token": access_token,
            "media_type": "CAROUSEL",
            "children": ",".join(children),
        }

        if caption:
            params["caption"] = caption[:2200]

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{GRAPH_API_BASE}/{instagram_user_id}/media",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            return data["id"]

    async def create_reel_container(
        self,
        instagram_user_id: str,
        access_token: str,
        video_url: str,
        caption: Optional[str] = None,
        cover_url: Optional[str] = None,
        share_to_feed: bool = True,
    ) -> str:
        """
        Create a Reel container.

        Args:
            instagram_user_id: Instagram Business Account ID
            access_token: Access token
            video_url: Publicly accessible video URL
            caption: Reel caption
            cover_url: Thumbnail image URL
            share_to_feed: Also share to main feed

        Returns:
            Reel container ID

        Requirements:
            - 3-90 seconds duration
            - 9:16 aspect ratio recommended
            - Max 100MB file size
        """
        params = {
            "access_token": access_token,
            "media_type": "REELS",
            "video_url": video_url,
        }

        if caption:
            params["caption"] = caption[:2200]
        if cover_url:
            params["cover_url"] = cover_url
        if share_to_feed:
            params["share_to_feed"] = "true"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{GRAPH_API_BASE}/{instagram_user_id}/media",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            return data["id"]

    async def publish_container(
        self,
        instagram_user_id: str,
        access_token: str,
        container_id: str,
    ) -> Dict[str, Any]:
        """
        Publish a media container (Step 2 of publishing).

        Args:
            instagram_user_id: Instagram Business Account ID
            access_token: Access token
            container_id: Container ID from create_*_container()

        Returns:
            {
                "id": "published_media_id"
            }

        Note:
            Wait for container status to be FINISHED before publishing.
            You can check status with get_container_status().
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{GRAPH_API_BASE}/{instagram_user_id}/media_publish",
                params={
                    "access_token": access_token,
                    "creation_id": container_id,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_container_status(
        self,
        container_id: str,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Check the status of a media container.

        Args:
            container_id: Container ID
            access_token: Access token

        Returns:
            {
                "id": "container_id",
                "status_code": "FINISHED" | "IN_PROGRESS" | "ERROR",
                "status": "Published" | "Processing" | "Error details"
            }
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GRAPH_API_BASE}/{container_id}",
                params={
                    "fields": "id,status_code,status",
                    "access_token": access_token,
                },
            )
            response.raise_for_status()
            return response.json()

    async def publish_photo(
        self,
        instagram_user_id: str,
        access_token: str,
        image_url: str,
        caption: Optional[str] = None,
        wait_for_completion: bool = True,
    ) -> Dict[str, Any]:
        """
        Convenience method: Create and publish a photo in one call.

        Args:
            instagram_user_id: Instagram Business Account ID
            access_token: Access token
            image_url: Publicly accessible image URL
            caption: Post caption
            wait_for_completion: Wait for container to be ready before publishing

        Returns:
            Published media info
        """
        # Create container
        container_id = await self.create_media_container(
            instagram_user_id=instagram_user_id,
            access_token=access_token,
            image_url=image_url,
            caption=caption,
        )

        # Wait for processing if needed
        if wait_for_completion:
            import asyncio
            max_attempts = 30
            for _ in range(max_attempts):
                status = await self.get_container_status(container_id, access_token)
                if status.get("status_code") == "FINISHED":
                    break
                elif status.get("status_code") == "ERROR":
                    raise Exception(f"Container creation failed: {status.get('status')}")
                await asyncio.sleep(2)

        # Publish
        result = await self.publish_container(
            instagram_user_id, access_token, container_id
        )
        return result

    async def publish_reel(
        self,
        instagram_user_id: str,
        access_token: str,
        video_url: str,
        caption: Optional[str] = None,
        cover_url: Optional[str] = None,
        share_to_feed: bool = True,
        wait_for_completion: bool = True,
    ) -> Dict[str, Any]:
        """
        Convenience method: Create and publish a reel in one call.

        Args:
            instagram_user_id: Instagram Business Account ID
            access_token: Access token
            video_url: Publicly accessible video URL
            caption: Reel caption
            cover_url: Thumbnail URL
            share_to_feed: Also share to feed
            wait_for_completion: Wait for processing

        Returns:
            Published reel info
        """
        container_id = await self.create_reel_container(
            instagram_user_id=instagram_user_id,
            access_token=access_token,
            video_url=video_url,
            caption=caption,
            cover_url=cover_url,
            share_to_feed=share_to_feed,
        )

        if wait_for_completion:
            import asyncio
            max_attempts = 60  # Reels take longer
            for _ in range(max_attempts):
                status = await self.get_container_status(container_id, access_token)
                if status.get("status_code") == "FINISHED":
                    break
                elif status.get("status_code") == "ERROR":
                    raise Exception(f"Reel creation failed: {status.get('status')}")
                await asyncio.sleep(3)

        result = await self.publish_container(
            instagram_user_id, access_token, container_id
        )
        return result

    async def publish_carousel(
        self,
        instagram_user_id: str,
        access_token: str,
        media_urls: List[str],
        caption: Optional[str] = None,
        wait_for_completion: bool = True,
    ) -> Dict[str, Any]:
        """
        Convenience method: Create and publish a carousel.

        Args:
            instagram_user_id: Instagram Business Account ID
            access_token: Access token
            media_urls: List of image/video URLs (2-10 items)
            caption: Album caption
            wait_for_completion: Wait for processing

        Returns:
            Published carousel info
        """
        if len(media_urls) < 2 or len(media_urls) > 10:
            raise ValueError("Carousel must have 2-10 items")

        # Create container for each item
        children = []
        for url in media_urls:
            is_video = any(url.lower().endswith(ext) for ext in ['.mp4', '.mov'])
            container_id = await self.create_media_container(
                instagram_user_id=instagram_user_id,
                access_token=access_token,
                image_url=None if is_video else url,
                video_url=url if is_video else None,
                is_carousel_item=True,
            )
            children.append(container_id)

        # Wait for all children to be ready
        if wait_for_completion:
            import asyncio
            for child_id in children:
                max_attempts = 30
                for _ in range(max_attempts):
                    status = await self.get_container_status(child_id, access_token)
                    if status.get("status_code") == "FINISHED":
                        break
                    elif status.get("status_code") == "ERROR":
                        raise Exception(f"Item creation failed: {status.get('status')}")
                    await asyncio.sleep(2)

        # Create carousel container
        carousel_id = await self.create_carousel_container(
            instagram_user_id=instagram_user_id,
            access_token=access_token,
            children=children,
            caption=caption,
        )

        # Publish
        result = await self.publish_container(
            instagram_user_id, access_token, carousel_id
        )
        return result

    # ========================================
    # Helper Methods
    # ========================================

    async def get_full_insights_data(
        self,
        instagram_user_id: str,
        access_token: str,
        limit_media: int = 50,
    ) -> Dict[str, Any]:
        """
        Get comprehensive insights data for an account.

        This is a convenience method that fetches:
        - Account info
        - Account-level insights (30 days)
        - Recent media with insights
        - Audience demographics

        Args:
            instagram_user_id: Instagram Business Account ID
            access_token: Access token
            limit_media: Number of recent posts to fetch

        Returns:
            {
                "account": {...},
                "account_insights": {...},
                "media": [...],
                "audience": {...},
                "fetched_at": "2024-11-29T12:00:00"
            }
        """
        # Fetch all data in parallel
        account_info = await self.get_account_info(access_token)
        account_insights = await self.get_account_insights(
            instagram_user_id, access_token
        )
        media_list = await self.get_media_list(
            instagram_user_id, access_token, limit=limit_media
        )
        audience = await self.get_audience_insights(instagram_user_id, access_token)

        # Fetch insights for each media item
        media_with_insights = []
        for media in media_list.get("data", []):
            try:
                insights = await self.get_media_insights(media["id"], access_token)
                media_with_insights.append({
                    **media,
                    "insights": insights.get("data", [])
                })
            except Exception as e:
                logger.warning(f"Failed to fetch insights for media {media['id']}: {e}")
                media_with_insights.append(media)

        return {
            "account": account_info,
            "account_insights": account_insights.get("data", []),
            "media": media_with_insights,
            "audience": audience.get("data", []),
            "fetched_at": datetime.utcnow().isoformat(),
        }


# Singleton instance
_instagram_api = None


def get_instagram_api() -> InstagramGraphAPI:
    """Get singleton Instagram API client."""
    global _instagram_api
    if _instagram_api is None:
        _instagram_api = InstagramGraphAPI()
    return _instagram_api
