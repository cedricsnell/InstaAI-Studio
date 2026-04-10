"""
Instagram Graph API client for Business accounts.
Handles OAuth, insights, posts, and audience data.

All requests go through _request() which provides:
  - Exponential backoff retry on rate limits (HTTP 429 + error codes #4, #17, #32, #613)
  - Retry on transient server errors (5xx)
  - No retry on auth or permanent client errors (4xx non-rate-limit)
  - Shared httpx.AsyncClient per instance (connection pooling)
"""
import asyncio
import os
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)

# Instagram Graph API endpoints
GRAPH_API_BASE = "https://graph.facebook.com/v18.0"
OAUTH_BASE = "https://api.instagram.com"

# Instagram error codes that indicate rate limiting
# https://developers.facebook.com/docs/graph-api/overview/rate-limiting/
RATE_LIMIT_CODES = {4, 17, 32, 613}

# Retry configuration
MAX_RETRIES = 4
BACKOFF_MIN = 2      # seconds
BACKOFF_MAX = 120    # seconds
BACKOFF_MULTIPLIER = 2


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class InstagramRateLimitError(Exception):
    """Raised when Instagram rate limit is hit and retries are exhausted."""
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class InstagramAPIError(Exception):
    """Non-retryable Instagram API error (auth failures, invalid params, etc.)."""
    def __init__(self, message: str, code: int = 0, subcode: int = 0, http_status: int = 0):
        super().__init__(message)
        self.code = code
        self.subcode = subcode
        self.http_status = http_status


# ---------------------------------------------------------------------------
# Helper: parse Instagram error payload
# ---------------------------------------------------------------------------

def _parse_instagram_error(response: httpx.Response) -> Optional[Dict[str, Any]]:
    """
    Extract the error object from an Instagram API error response.

    Instagram wraps errors as:
      {"error": {"message": "...", "type": "...", "code": 17, "error_subcode": ...}}
    """
    try:
        body = response.json()
        return body.get("error")
    except Exception:
        return None


def _is_rate_limit_response(response: httpx.Response) -> bool:
    """Return True if the response represents a rate limit error."""
    if response.status_code == 429:
        return True
    if response.status_code in (400, 403):
        err = _parse_instagram_error(response)
        if err and err.get("code") in RATE_LIMIT_CODES:
            return True
    return False


def _is_retryable_server_error(response: httpx.Response) -> bool:
    """Return True for transient 5xx errors worth retrying."""
    return response.status_code >= 500


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------

class InstagramGraphAPI:
    """Client for Instagram Graph API (Business accounts only)."""

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ):
        self.app_id = app_id or os.getenv("INSTAGRAM_APP_ID")
        self.app_secret = app_secret or os.getenv("INSTAGRAM_APP_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("INSTAGRAM_REDIRECT_URI")

        if not all([self.app_id, self.app_secret, self.redirect_uri]):
            logger.warning(
                "Instagram credentials not fully configured. "
                "Set INSTAGRAM_APP_ID, INSTAGRAM_APP_SECRET, and INSTAGRAM_REDIRECT_URI"
            )

        # Shared client — reused across requests for connection pooling
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))

    # -----------------------------------------------------------------------
    # Core request method with retry + backoff
    # -----------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Make an API request with exponential backoff for rate limits and 5xx errors.

        Args:
            method:  HTTP method ("GET" or "POST")
            url:     Full URL
            params:  Query parameters
            data:    Form data (POST only)
            timeout: Override default 30s timeout

        Returns:
            Parsed JSON response body

        Raises:
            InstagramRateLimitError: Rate limit hit after all retries
            InstagramAPIError:       Non-retryable API or auth error
            httpx.TimeoutException:  Request timed out after retries
        """
        client_timeout = httpx.Timeout(timeout or 30.0, connect=10.0)
        last_error: Optional[Exception] = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                if method.upper() == "GET":
                    response = await self._client.get(url, params=params, timeout=client_timeout)
                else:
                    response = await self._client.post(url, params=params, data=data, timeout=client_timeout)

                # ── Rate limit ─────────────────────────────────────────────
                if _is_rate_limit_response(response):
                    err = _parse_instagram_error(response)
                    err_code = err.get("code", 0) if err else 0
                    err_msg = err.get("message", "Rate limit reached") if err else "Rate limit reached"

                    retry_after = int(response.headers.get("Retry-After", 60))
                    wait = min(BACKOFF_MIN * (BACKOFF_MULTIPLIER ** attempt), BACKOFF_MAX)
                    wait = max(wait, retry_after)

                    if attempt < MAX_RETRIES:
                        logger.warning(
                            "Instagram rate limit (code #%s, attempt %d/%d). "
                            "Waiting %ds before retry.",
                            err_code, attempt + 1, MAX_RETRIES, wait,
                        )
                        await asyncio.sleep(wait)
                        last_error = InstagramRateLimitError(err_msg, retry_after=retry_after)
                        continue
                    else:
                        raise InstagramRateLimitError(
                            f"Rate limit exhausted after {MAX_RETRIES} retries: {err_msg}",
                            retry_after=retry_after,
                        )

                # ── Transient server error ─────────────────────────────────
                if _is_retryable_server_error(response):
                    wait = min(BACKOFF_MIN * (BACKOFF_MULTIPLIER ** attempt), BACKOFF_MAX)
                    if attempt < MAX_RETRIES:
                        logger.warning(
                            "Instagram API server error %d (attempt %d/%d). Waiting %ds.",
                            response.status_code, attempt + 1, MAX_RETRIES, wait,
                        )
                        await asyncio.sleep(wait)
                        last_error = httpx.HTTPStatusError(
                            f"Server error {response.status_code}",
                            request=response.request,
                            response=response,
                        )
                        continue
                    else:
                        response.raise_for_status()

                # ── Non-retryable client error ─────────────────────────────
                if response.status_code >= 400:
                    err = _parse_instagram_error(response)
                    if err:
                        raise InstagramAPIError(
                            err.get("message", f"API error {response.status_code}"),
                            code=err.get("code", 0),
                            subcode=err.get("error_subcode", 0),
                            http_status=response.status_code,
                        )
                    response.raise_for_status()

                # ── Success ────────────────────────────────────────────────
                return response.json()

            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as exc:
                wait = min(BACKOFF_MIN * (BACKOFF_MULTIPLIER ** attempt), BACKOFF_MAX)
                if attempt < MAX_RETRIES:
                    logger.warning(
                        "Instagram API network error (%s, attempt %d/%d). Waiting %ds.",
                        type(exc).__name__, attempt + 1, MAX_RETRIES, wait,
                    )
                    await asyncio.sleep(wait)
                    last_error = exc
                    continue
                raise

        # Should not reach here, but satisfy type checker
        if last_error:
            raise last_error
        raise RuntimeError("Unexpected exit from retry loop")

    # -----------------------------------------------------------------------
    # OAuth Flow
    # -----------------------------------------------------------------------

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Get Instagram OAuth authorization URL."""
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
        """Exchange authorization code for short-lived access token."""
        return await self._request(
            "POST",
            f"{OAUTH_BASE}/oauth/access_token",
            data={
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
                "code": code,
            },
        )

    async def get_long_lived_token(self, short_lived_token: str) -> Dict[str, Any]:
        """Exchange short-lived token for long-lived token (60 days)."""
        return await self._request(
            "GET",
            f"{GRAPH_API_BASE}/access_token",
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": self.app_secret,
                "access_token": short_lived_token,
            },
        )

    async def refresh_long_lived_token(self, access_token: str) -> Dict[str, Any]:
        """Refresh a long-lived token (extends by 60 days)."""
        return await self._request(
            "GET",
            f"{GRAPH_API_BASE}/refresh_access_token",
            params={
                "grant_type": "ig_refresh_token",
                "access_token": access_token,
            },
        )

    # -----------------------------------------------------------------------
    # Account Information
    # -----------------------------------------------------------------------

    async def get_account_info(self, access_token: str) -> Dict[str, Any]:
        """Get Instagram Business account information."""
        return await self._request(
            "GET",
            f"{GRAPH_API_BASE}/me",
            params={
                "fields": "id,username,account_type,media_count,followers_count,follows_count,profile_picture_url",
                "access_token": access_token,
            },
        )

    # -----------------------------------------------------------------------
    # Insights (Analytics)
    # -----------------------------------------------------------------------

    async def get_account_insights(
        self,
        instagram_user_id: str,
        access_token: str,
        period: str = "day",
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get account-level insights."""
        if not since:
            since = datetime.utcnow() - timedelta(days=30)
        if not until:
            until = datetime.utcnow()

        metrics = [
            "impressions", "reach", "follower_count", "email_contacts",
            "phone_call_clicks", "text_message_clicks", "get_directions_clicks",
            "website_clicks", "profile_views",
        ]
        return await self._request(
            "GET",
            f"{GRAPH_API_BASE}/{instagram_user_id}/insights",
            params={
                "metric": ",".join(metrics),
                "period": period,
                "since": int(since.timestamp()),
                "until": int(until.timestamp()),
                "access_token": access_token,
            },
        )

    async def get_media_list(
        self,
        instagram_user_id: str,
        access_token: str,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get list of media (posts) for the account."""
        return await self._request(
            "GET",
            f"{GRAPH_API_BASE}/{instagram_user_id}/media",
            params={
                "fields": "id,media_type,media_url,permalink,caption,timestamp,like_count,comments_count,thumbnail_url",
                "limit": min(limit, 100),
                "access_token": access_token,
            },
        )

    async def get_media_insights(
        self,
        media_id: str,
        access_token: str,
    ) -> Dict[str, Any]:
        """Get insights for a specific media item."""
        metrics = ["engagement", "impressions", "reach", "saved", "video_views"]
        return await self._request(
            "GET",
            f"{GRAPH_API_BASE}/{media_id}/insights",
            params={
                "metric": ",".join(metrics),
                "access_token": access_token,
            },
        )

    async def get_audience_insights(
        self,
        instagram_user_id: str,
        access_token: str,
        period: str = "lifetime",
    ) -> Dict[str, Any]:
        """Get audience demographic insights."""
        metrics = [
            "audience_gender_age", "audience_locale", "audience_country",
            "audience_city", "online_followers",
        ]
        return await self._request(
            "GET",
            f"{GRAPH_API_BASE}/{instagram_user_id}/insights",
            params={
                "metric": ",".join(metrics),
                "period": period,
                "access_token": access_token,
            },
        )

    # -----------------------------------------------------------------------
    # Content Publishing
    # -----------------------------------------------------------------------

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
        """Create a media container (Step 1 of publishing). Returns container ID."""
        if not image_url and not video_url:
            raise ValueError("Either image_url or video_url must be provided")

        params: Dict[str, Any] = {"access_token": access_token}

        if image_url:
            params["image_url"] = image_url
        if video_url:
            params["video_url"] = video_url
            params["media_type"] = "VIDEO"
            if cover_url:
                params["cover_url"] = cover_url
        if caption and not is_carousel_item:
            params["caption"] = caption[:2200]
        if location_id:
            params["location_id"] = location_id
        if user_tags:
            params["user_tags"] = user_tags
        if is_carousel_item:
            params["is_carousel_item"] = "true"

        data = await self._request(
            "POST",
            f"{GRAPH_API_BASE}/{instagram_user_id}/media",
            params=params,
            timeout=60.0,
        )
        return data["id"]

    async def create_carousel_container(
        self,
        instagram_user_id: str,
        access_token: str,
        children: List[str],
        caption: Optional[str] = None,
    ) -> str:
        """Create a carousel album container. Returns container ID."""
        if len(children) < 2 or len(children) > 10:
            raise ValueError("Carousel must have 2-10 items")

        params: Dict[str, Any] = {
            "access_token": access_token,
            "media_type": "CAROUSEL",
            "children": ",".join(children),
        }
        if caption:
            params["caption"] = caption[:2200]

        data = await self._request(
            "POST",
            f"{GRAPH_API_BASE}/{instagram_user_id}/media",
            params=params,
            timeout=60.0,
        )
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
        """Create a Reel container. Returns container ID."""
        params: Dict[str, Any] = {
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

        data = await self._request(
            "POST",
            f"{GRAPH_API_BASE}/{instagram_user_id}/media",
            params=params,
            timeout=120.0,
        )
        return data["id"]

    async def publish_container(
        self,
        instagram_user_id: str,
        access_token: str,
        container_id: str,
    ) -> Dict[str, Any]:
        """Publish a media container (Step 2 of publishing)."""
        return await self._request(
            "POST",
            f"{GRAPH_API_BASE}/{instagram_user_id}/media_publish",
            params={
                "access_token": access_token,
                "creation_id": container_id,
            },
            timeout=60.0,
        )

    async def get_container_status(
        self,
        container_id: str,
        access_token: str,
    ) -> Dict[str, Any]:
        """Check the processing status of a media container."""
        return await self._request(
            "GET",
            f"{GRAPH_API_BASE}/{container_id}",
            params={
                "fields": "id,status_code,status",
                "access_token": access_token,
            },
        )

    async def _wait_for_container(
        self,
        container_id: str,
        access_token: str,
        max_attempts: int = 30,
        poll_interval: float = 2.0,
    ) -> None:
        """Poll container status until FINISHED or ERROR."""
        for _ in range(max_attempts):
            status = await self.get_container_status(container_id, access_token)
            code = status.get("status_code")
            if code == "FINISHED":
                return
            if code == "ERROR":
                raise InstagramAPIError(
                    f"Container processing failed: {status.get('status')}",
                    http_status=0,
                )
            await asyncio.sleep(poll_interval)
        raise InstagramAPIError(
            f"Container {container_id} did not finish processing after "
            f"{max_attempts * poll_interval:.0f}s",
            http_status=0,
        )

    # -----------------------------------------------------------------------
    # Convenience publish methods
    # -----------------------------------------------------------------------

    async def publish_photo(
        self,
        instagram_user_id: str,
        access_token: str,
        image_url: str,
        caption: Optional[str] = None,
        wait_for_completion: bool = True,
    ) -> Dict[str, Any]:
        """Create and publish a photo in one call."""
        container_id = await self.create_media_container(
            instagram_user_id=instagram_user_id,
            access_token=access_token,
            image_url=image_url,
            caption=caption,
        )
        if wait_for_completion:
            await self._wait_for_container(container_id, access_token)
        return await self.publish_container(instagram_user_id, access_token, container_id)

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
        """Create and publish a reel in one call."""
        container_id = await self.create_reel_container(
            instagram_user_id=instagram_user_id,
            access_token=access_token,
            video_url=video_url,
            caption=caption,
            cover_url=cover_url,
            share_to_feed=share_to_feed,
        )
        if wait_for_completion:
            # Reels take longer to process
            await self._wait_for_container(container_id, access_token, max_attempts=60, poll_interval=3.0)
        return await self.publish_container(instagram_user_id, access_token, container_id)

    async def publish_carousel(
        self,
        instagram_user_id: str,
        access_token: str,
        media_urls: List[str],
        caption: Optional[str] = None,
        wait_for_completion: bool = True,
    ) -> Dict[str, Any]:
        """Create and publish a carousel in one call."""
        if len(media_urls) < 2 or len(media_urls) > 10:
            raise ValueError("Carousel must have 2-10 items")

        children = []
        for url in media_urls:
            is_video = any(url.lower().endswith(ext) for ext in [".mp4", ".mov"])
            container_id = await self.create_media_container(
                instagram_user_id=instagram_user_id,
                access_token=access_token,
                image_url=None if is_video else url,
                video_url=url if is_video else None,
                is_carousel_item=True,
            )
            children.append(container_id)

        if wait_for_completion:
            for child_id in children:
                await self._wait_for_container(child_id, access_token)

        carousel_id = await self.create_carousel_container(
            instagram_user_id=instagram_user_id,
            access_token=access_token,
            children=children,
            caption=caption,
        )
        return await self.publish_container(instagram_user_id, access_token, carousel_id)

    # -----------------------------------------------------------------------
    # Comprehensive data fetch
    # -----------------------------------------------------------------------

    async def get_full_insights_data(
        self,
        instagram_user_id: str,
        access_token: str,
        limit_media: int = 50,
    ) -> Dict[str, Any]:
        """
        Fetch account info, account-level insights, recent media with per-post
        insights, and audience demographics in one call.
        """
        account_info, account_insights, media_list, audience = await asyncio.gather(
            self.get_account_info(access_token),
            self.get_account_insights(instagram_user_id, access_token),
            self.get_media_list(instagram_user_id, access_token, limit=limit_media),
            self.get_audience_insights(instagram_user_id, access_token),
        )

        media_with_insights = []
        for media in media_list.get("data", []):
            try:
                insights = await self.get_media_insights(media["id"], access_token)
                media_with_insights.append({**media, "insights": insights.get("data", [])})
            except (InstagramAPIError, InstagramRateLimitError) as e:
                logger.warning("Failed to fetch insights for media %s: %s", media["id"], e)
                media_with_insights.append(media)

        return {
            "account": account_info,
            "account_insights": account_insights.get("data", []),
            "media": media_with_insights,
            "audience": audience.get("data", []),
            "fetched_at": datetime.utcnow().isoformat(),
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_instagram_api: Optional[InstagramGraphAPI] = None


def get_instagram_api() -> InstagramGraphAPI:
    """Get or create the singleton Instagram API client."""
    global _instagram_api
    if _instagram_api is None:
        _instagram_api = InstagramGraphAPI()
    return _instagram_api
