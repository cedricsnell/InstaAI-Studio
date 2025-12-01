"""
Celery tasks for Instagram operations
"""
import logging
from typing import Dict, Any
from datetime import datetime, timedelta

from .celery_app import celery_app
from ..database.database import SessionLocal
from ..database.models import InstagramAccount, InstagramPost
from ..instagram.graph_api import get_instagram_api
from dateutil.parser import parse as parse_date

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="src.tasks.instagram_tasks.sync_account_media")
def sync_account_media(self, account_id: int, limit: int = 100) -> Dict[str, Any]:
    """
    Sync media for a specific Instagram account.

    Args:
        account_id: Instagram account ID
        limit: Max posts to fetch

    Returns:
        Sync summary
    """
    db = SessionLocal()

    try:
        logger.info(f"Syncing media for account {account_id}")

        account = db.query(InstagramAccount).filter(
            InstagramAccount.id == account_id,
            InstagramAccount.is_active == True
        ).first()

        if not account:
            return {"success": False, "error": "Account not found"}

        if account.token_expires_at < datetime.utcnow():
            return {"success": False, "error": "Token expired"}

        api = get_instagram_api()

        # Fetch media
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        media_response = loop.run_until_complete(
            api.get_media_list(
                instagram_user_id=account.instagram_user_id,
                access_token=account.access_token,
                limit=min(limit, 200)
            )
        )

        media_items = media_response.get("data", [])
        new_posts = 0
        updated_posts = 0

        for media in media_items:
            media_id = media.get("id")

            existing_post = db.query(InstagramPost).filter(
                InstagramPost.media_id == media_id
            ).first()

            timestamp_str = media.get("timestamp")
            timestamp = parse_date(timestamp_str) if timestamp_str else datetime.utcnow()

            # Try to get insights
            insights_data = {}
            try:
                insights_response = loop.run_until_complete(
                    api.get_media_insights(media_id, account.access_token)
                )
                for insight in insights_response.get("data", []):
                    name = insight.get("name")
                    values = insight.get("values", [])
                    if values:
                        insights_data[name] = values[0].get("value", 0)
            except:
                pass

            likes = media.get("like_count", 0)
            comments = media.get("comments_count", 0)
            saves = insights_data.get("saved", 0)
            impressions = insights_data.get("impressions", 0)

            engagement_rate = 0.0
            if impressions > 0:
                engagement_rate = ((likes + comments + saves) / impressions) * 100

            if existing_post:
                existing_post.likes_count = likes
                existing_post.comments_count = comments
                existing_post.saves_count = saves
                existing_post.impressions = impressions
                existing_post.engagement_rate = engagement_rate
                existing_post.updated_at = datetime.utcnow()
                updated_posts += 1
            else:
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
                    impressions=impressions,
                    engagement_rate=engagement_rate,
                )
                db.add(new_post)
                new_posts += 1

        account.last_synced_at = datetime.utcnow()
        db.commit()

        logger.info(f"✅ Synced {new_posts} new, {updated_posts} updated posts")
        return {
            "success": True,
            "account_id": account_id,
            "new_posts": new_posts,
            "updated_posts": updated_posts,
            "total_fetched": len(media_items)
        }

    except Exception as e:
        logger.error(f"Media sync failed: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}

    finally:
        db.close()


@celery_app.task(bind=True, name="src.tasks.instagram_tasks.sync_all_accounts")
def sync_all_accounts(self) -> Dict[str, Any]:
    """
    Sync media for all active accounts (scheduled task).

    Returns:
        Summary of all syncs
    """
    db = SessionLocal()

    try:
        logger.info("Starting batch media sync for all accounts")

        accounts = db.query(InstagramAccount).filter(
            InstagramAccount.is_active == True
        ).all()

        results = []
        for account in accounts:
            try:
                result = sync_account_media.delay(account.id, limit=50)
                results.append({
                    "account_id": account.id,
                    "task_id": result.id,
                    "username": account.username
                })
            except Exception as e:
                logger.error(f"Failed to queue sync for account {account.id}: {e}")

        logger.info(f"✅ Queued sync for {len(results)} accounts")
        return {
            "success": True,
            "accounts_synced": len(results),
            "tasks": results
        }

    except Exception as e:
        logger.error(f"Batch sync failed: {e}")
        return {"success": False, "error": str(e)}

    finally:
        db.close()


@celery_app.task(bind=True, name="src.tasks.instagram_tasks.refresh_expiring_tokens")
def refresh_expiring_tokens(self) -> Dict[str, Any]:
    """
    Refresh Instagram access tokens that are expiring soon.

    Returns:
        Summary of refreshed tokens
    """
    db = SessionLocal()

    try:
        logger.info("Refreshing expiring tokens")

        # Find tokens expiring in next 7 days
        expiry_threshold = datetime.utcnow() + timedelta(days=7)

        accounts = db.query(InstagramAccount).filter(
            InstagramAccount.is_active == True,
            InstagramAccount.token_expires_at < expiry_threshold
        ).all()

        api = get_instagram_api()
        refreshed = 0
        failed = 0

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        for account in accounts:
            try:
                # Refresh token
                token_data = loop.run_until_complete(
                    api.refresh_long_lived_token(account.access_token)
                )

                account.access_token = token_data["access_token"]
                account.token_expires_at = datetime.utcnow() + timedelta(
                    seconds=token_data.get("expires_in", 5184000)
                )
                refreshed += 1

                logger.info(f"✅ Refreshed token for @{account.username}")

            except Exception as e:
                logger.error(f"Failed to refresh token for {account.username}: {e}")
                failed += 1

        db.commit()

        logger.info(f"Token refresh complete: {refreshed} success, {failed} failed")
        return {
            "success": True,
            "refreshed": refreshed,
            "failed": failed,
            "total_checked": len(accounts)
        }

    except Exception as e:
        logger.error(f"Token refresh batch failed: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}

    finally:
        db.close()
