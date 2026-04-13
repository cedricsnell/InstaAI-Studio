"""
Instagram OAuth callback handler.

Instagram redirects here after the user authorizes the app:
  GET /auth/instagram/callback?code=XXX&state=user_123

This endpoint completes the full connection flow server-side:
  1. Exchange code for short-lived token
  2. Exchange for long-lived token (60 days)
  3. Fetch account info
  4. Save/update InstagramAccount in DB
  5. Redirect to the mobile deep link (instaaistudio://auth/instagram/callback)
     so WebBrowser.openAuthSessionAsync resolves as 'success'.
     Falls back to an HTML page for web / non-mobile contexts.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode
import os
import logging

from ...database import get_db
from ...database.models import InstagramAccount, User
from ...instagram.graph_api import get_instagram_api

# Deep link scheme for the mobile app.  Override with MOBILE_DEEP_LINK_SCHEME env var if needed.
_MOBILE_SCHEME = os.getenv("MOBILE_DEEP_LINK_SCHEME", "instaaistudio")
_MOBILE_CALLBACK = f"{_MOBILE_SCHEME}://auth/instagram/callback"

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/instagram/callback", response_class=HTMLResponse)
async def instagram_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_reason: Optional[str] = None,
    error_description: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Handle Instagram OAuth redirect.
    Called by Instagram after the user authorizes (or denies) the app.
    """

    # ── User denied authorization ─────────────────────────────────────────
    if error:
        logger.warning(f"Instagram OAuth denied: {error} — {error_reason}")
        return _redirect_or_page(
            success=False,
            error_msg=error_description or error_reason or error,
        )

    if not code or not state:
        return _redirect_or_page(success=False, error_msg="Missing code or state parameter")

    # ── Extract user from state (format: "user_{id}") ────────────────────
    try:
        user_id = int(state.replace("user_", ""))
    except (ValueError, AttributeError):
        return _redirect_or_page(success=False, error_msg="Invalid state parameter")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        return _redirect_or_page(success=False, error_msg="User account not found")

    # ── OAuth token exchange ──────────────────────────────────────────────
    api = get_instagram_api()

    try:
        # Step 1: short-lived token
        token_data = await api.exchange_code_for_token(code)
        short_lived_token = token_data["access_token"]

        # Step 2: long-lived token (60 days)
        long_lived_data = await api.get_long_lived_token(short_lived_token)
        access_token = long_lived_data["access_token"]
        expires_in = long_lived_data.get("expires_in", 5184000)

        # Step 3: fetch account info
        account_info = await api.get_account_info(access_token)

        account_type = account_info.get("account_type", "")
        if account_type not in ["BUSINESS", "MEDIA_CREATOR"]:
            return _redirect_or_page(
                success=False,
                error_msg=f"Only Business or Creator accounts are supported (yours: {account_type or 'Personal'})",
            )

        # Step 4: save or update
        existing = db.query(InstagramAccount).filter(
            InstagramAccount.instagram_user_id == account_info["id"]
        ).first()

        username = account_info.get("username", "unknown")
        followers = account_info.get("followers_count", 0)

        if existing:
            existing.access_token = access_token
            existing.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            existing.username = username
            existing.account_type = account_type
            existing.followers_count = followers
            existing.profile_picture_url = account_info.get("profile_picture_url")
            existing.is_active = True
            existing.user_id = user_id
            existing.updated_at = datetime.utcnow()
        else:
            db.add(InstagramAccount(
                user_id=user_id,
                instagram_user_id=account_info["id"],
                username=username,
                account_type=account_type,
                access_token=access_token,
                token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                profile_picture_url=account_info.get("profile_picture_url"),
                followers_count=followers,
                media_count=account_info.get("media_count", 0),
                is_active=True,
            ))

        db.commit()
        logger.info(f"Instagram account @{username} connected for user {user_id}")

        return _redirect_or_page(success=True, username=username)

    except Exception as e:
        logger.error(f"Instagram OAuth callback failed for user {user_id}: {e}")
        return _redirect_or_page(success=False, error_msg=str(e))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _redirect_or_page(
    success: bool,
    username: Optional[str] = None,
    error_msg: Optional[str] = None,
):
    """
    Redirect to the mobile deep link so WebBrowser.openAuthSessionAsync resolves.
    Falls back to an HTML page (e.g., when opened in a plain browser on web).
    """
    params: dict = {"success": "true" if success else "false"}
    if username:
        params["username"] = username
    if error_msg:
        params["error"] = error_msg[:200]  # cap length for URL safety

    deep_link = f"{_MOBILE_CALLBACK}?{urlencode(params)}"
    # 302 redirect — Expo's WebBrowser intercepts this and returns {type: 'success'}
    return RedirectResponse(url=deep_link, status_code=302)


def _html_page(title: str, body: str, success: bool = True) -> HTMLResponse:
    """Fallback HTML page (kept for direct browser access / debugging)."""
    icon = "✅" if success else "❌"
    color = "#22c55e" if success else "#ef4444"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>InstaAI — {title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #0f0f0f; color: #f0f0f0; display: flex; align-items: center;
           justify-content: center; min-height: 100vh; margin: 0; }}
    .card {{ background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 16px;
             padding: 48px; max-width: 480px; text-align: center; }}
    .icon {{ font-size: 3em; margin-bottom: 16px; }}
    h2 {{ color: {color}; margin: 0 0 16px; }}
    p {{ color: #aaa; line-height: 1.6; }}
    strong {{ color: #f0f0f0; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">{icon}</div>
    <h2>{title}</h2>
    {body}
  </div>
</body>
</html>"""
    status_code = 200 if success else 400
    return HTMLResponse(content=html, status_code=status_code)
