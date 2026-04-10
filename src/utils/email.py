"""
Transactional email via Resend.

Required env vars:
  RESEND_API_KEY  — from resend.com dashboard
  FROM_EMAIL      — verified sender address (default: noreply@instaaistudio.com)
  FRONTEND_URL    — base URL for links in emails (default: https://instaaistudio.netlify.app)

All send functions return True on success, False on failure. They never raise —
email delivery failure must not break registration or other flows.
"""
import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://instaaistudio.netlify.app")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@instaaistudio.com")


def _get_resend():
    """Return the resend module if API key is configured, else None."""
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        logger.warning("RESEND_API_KEY not set — emails will not be sent")
        return None
    try:
        import resend
        resend.api_key = api_key
        return resend
    except ImportError:
        logger.error("resend package not installed — pip install resend")
        return None


async def send_verification_email(
    to_email: str,
    token: str,
    full_name: Optional[str] = None,
) -> bool:
    """
    Send an email verification link.

    The link points to FRONTEND_URL/verify-email?token=<token>. The frontend
    should call POST /api/auth/verify-email with the token.
    """
    resend = _get_resend()
    if not resend:
        logger.info("[DEV] Verification token for %s: %s", to_email, token)
        return False

    name = full_name or to_email.split("@")[0]
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"

    html = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                max-width:560px;margin:0 auto;padding:32px;background:#0f0f0f;color:#f0f0f0;
                border-radius:12px;">
      <h2 style="color:#a855f7;margin:0 0 8px;">Verify your email</h2>
      <p style="color:#aaa;">Hi {name},</p>
      <p style="color:#aaa;">Thanks for signing up for InstaAI Studio. Click the button below
         to verify your email address and activate your account.</p>
      <a href="{verify_url}"
         style="display:inline-block;margin:24px 0;padding:14px 28px;
                background:linear-gradient(135deg,#a855f7,#ec4899);
                color:#fff;text-decoration:none;border-radius:8px;font-weight:600;">
        Verify Email Address
      </a>
      <p style="color:#666;font-size:13px;">
        Or copy this link:<br>
        <a href="{verify_url}" style="color:#a855f7;word-break:break-all;">{verify_url}</a>
      </p>
      <p style="color:#666;font-size:13px;">This link expires in 24 hours.</p>
      <hr style="border:none;border-top:1px solid #2a2a2a;margin:24px 0;">
      <p style="color:#555;font-size:12px;">InstaAI Studio — Instagram Marketing Automation</p>
    </div>
    """

    try:
        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": f"InstaAI Studio <{FROM_EMAIL}>",
                "to": [to_email],
                "subject": "Verify your InstaAI Studio email",
                "html": html,
            },
        )
        logger.info("Verification email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send verification email to %s: %s", to_email, e)
        return False


async def send_password_reset_email(
    to_email: str,
    token: str,
    full_name: Optional[str] = None,
) -> bool:
    """Send a password reset link."""
    resend = _get_resend()
    if not resend:
        logger.info("[DEV] Password reset token for %s: %s", to_email, token)
        return False

    name = full_name or to_email.split("@")[0]
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"

    html = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                max-width:560px;margin:0 auto;padding:32px;background:#0f0f0f;color:#f0f0f0;
                border-radius:12px;">
      <h2 style="color:#a855f7;margin:0 0 8px;">Reset your password</h2>
      <p style="color:#aaa;">Hi {name},</p>
      <p style="color:#aaa;">We received a request to reset your password. Click below to choose a new one.</p>
      <a href="{reset_url}"
         style="display:inline-block;margin:24px 0;padding:14px 28px;
                background:linear-gradient(135deg,#a855f7,#ec4899);
                color:#fff;text-decoration:none;border-radius:8px;font-weight:600;">
        Reset Password
      </a>
      <p style="color:#666;font-size:13px;">This link expires in 30 minutes.</p>
      <p style="color:#666;font-size:13px;">If you didn't request this, you can ignore this email.</p>
      <hr style="border:none;border-top:1px solid #2a2a2a;margin:24px 0;">
      <p style="color:#555;font-size:12px;">InstaAI Studio — Instagram Marketing Automation</p>
    </div>
    """

    try:
        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": f"InstaAI Studio <{FROM_EMAIL}>",
                "to": [to_email],
                "subject": "Reset your InstaAI Studio password",
                "html": html,
            },
        )
        logger.info("Password reset email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send password reset email to %s: %s", to_email, e)
        return False
