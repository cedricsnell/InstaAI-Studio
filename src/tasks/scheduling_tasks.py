"""
Celery tasks for post scheduling and publishing
"""
import logging
from typing import Dict, Any
from datetime import datetime

from .celery_app import celery_app
from ..database.database import SessionLocal
from ..database.models import PostSchedule, ScheduleStatus, InstagramAccount
from ..instagram.graph_api import get_instagram_api

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="src.tasks.scheduling_tasks.publish_scheduled_post")
def publish_scheduled_post(self, schedule_id: int) -> Dict[str, Any]:
    """
    Publish a scheduled post to Instagram.

    Args:
        schedule_id: PostSchedule ID

    Returns:
        {"success": bool, "post_id": str}
    """
    db = SessionLocal()

    try:
        logger.info(f"Publishing scheduled post {schedule_id}")

        # Get scheduled post
        schedule = db.query(PostSchedule).filter(
            PostSchedule.id == schedule_id
        ).first()

        if not schedule:
            return {"success": False, "error": "Schedule not found"}

        if schedule.status != ScheduleStatus.SCHEDULED:
            return {"success": False, "error": f"Post status is {schedule.status}"}

        # Get account
        account = db.query(InstagramAccount).filter(
            InstagramAccount.id == schedule.instagram_account_id
        ).first()

        if not account or not account.is_active:
            schedule.status = ScheduleStatus.FAILED
            schedule.error_message = "Account not found or inactive"
            db.commit()
            return {"success": False, "error": "Account not available"}

        # Update status to publishing
        schedule.status = ScheduleStatus.PUBLISHING
        db.commit()

        # Publish based on post type
        api = get_instagram_api()

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            if schedule.post_type == "photo":
                result = loop.run_until_complete(
                    api.publish_photo(
                        instagram_user_id=account.instagram_user_id,
                        access_token=account.access_token,
                        image_url=schedule.media_url,
                        caption=schedule.caption,
                        wait_for_completion=True
                    )
                )
            elif schedule.post_type == "reel":
                result = loop.run_until_complete(
                    api.publish_reel(
                        instagram_user_id=account.instagram_user_id,
                        access_token=account.access_token,
                        video_url=schedule.media_url,
                        caption=schedule.caption,
                        wait_for_completion=True
                    )
                )
            elif schedule.post_type == "carousel":
                # Parse media URLs (stored as JSON string)
                import json
                media_urls = json.loads(schedule.carousel_media_urls or "[]")

                result = loop.run_until_complete(
                    api.publish_carousel(
                        instagram_user_id=account.instagram_user_id,
                        access_token=account.access_token,
                        media_urls=media_urls,
                        caption=schedule.caption,
                        wait_for_completion=True
                    )
                )
            else:
                raise ValueError(f"Unknown post type: {schedule.post_type}")

            # Update schedule with success
            schedule.status = ScheduleStatus.PUBLISHED
            schedule.instagram_post_id = result.get("id")
            schedule.posted_at = datetime.utcnow()
            db.commit()

            logger.info(f"✅ Published post {schedule_id}: {result.get('id')}")
            return {
                "success": True,
                "schedule_id": schedule_id,
                "instagram_post_id": result.get("id")
            }

        except Exception as e:
            # Mark as failed
            schedule.status = ScheduleStatus.FAILED
            schedule.error_message = str(e)
            db.commit()

            logger.error(f"Failed to publish post {schedule_id}: {e}")
            return {"success": False, "error": str(e)}

    except Exception as e:
        logger.error(f"Scheduling task failed: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}

    finally:
        db.close()


@celery_app.task(bind=True, name="src.tasks.scheduling_tasks.process_pending_posts")
def process_pending_posts(self) -> Dict[str, Any]:
    """
    Check for posts that need to be published (runs every 5 minutes).

    Returns:
        Summary of processed posts
    """
    db = SessionLocal()

    try:
        logger.info("Checking for pending scheduled posts")

        # Find posts scheduled for now or earlier
        now = datetime.utcnow()

        pending_posts = db.query(PostSchedule).filter(
            PostSchedule.status == ScheduleStatus.SCHEDULED,
            PostSchedule.scheduled_time <= now
        ).all()

        if not pending_posts:
            return {"success": True, "pending_posts": 0, "message": "No posts to publish"}

        logger.info(f"Found {len(pending_posts)} posts to publish")

        published = 0
        failed = 0

        for post in pending_posts:
            try:
                # Queue publishing task
                publish_scheduled_post.delay(post.id)
                published += 1
            except Exception as e:
                logger.error(f"Failed to queue post {post.id}: {e}")
                post.status = ScheduleStatus.FAILED
                post.error_message = f"Failed to queue: {str(e)}"
                failed += 1

        db.commit()

        logger.info(f"✅ Queued {published} posts, {failed} failed")
        return {
            "success": True,
            "queued": published,
            "failed": failed,
            "total_pending": len(pending_posts)
        }

    except Exception as e:
        logger.error(f"Process pending posts failed: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}

    finally:
        db.close()


@celery_app.task(bind=True, name="src.tasks.scheduling_tasks.schedule_content_post")
def schedule_content_post(
    self,
    content_id: int,
    account_id: int,
    scheduled_time: str,
    media_url: str,
    post_type: str = "reel"
) -> Dict[str, Any]:
    """
    Schedule generated content for publishing.

    Args:
        content_id: GeneratedContent ID
        account_id: Instagram account ID
        scheduled_time: ISO format datetime string
        media_url: URL to media file
        post_type: 'photo', 'reel', or 'carousel'

    Returns:
        {"success": bool, "schedule_id": int}
    """
    db = SessionLocal()

    try:
        from ..database.models import GeneratedContent

        # Get content
        content = db.query(GeneratedContent).filter(
            GeneratedContent.id == content_id
        ).first()

        if not content:
            return {"success": False, "error": "Content not found"}

        # Parse scheduled time
        from dateutil.parser import parse as parse_date
        scheduled_dt = parse_date(scheduled_time)

        # Create schedule
        schedule = PostSchedule(
            instagram_account_id=account_id,
            generated_content_id=content_id,
            scheduled_time=scheduled_dt,
            post_type=post_type,
            caption=content.suggested_caption,
            hashtags=content.suggested_hashtags,
            media_url=media_url,
            status=ScheduleStatus.SCHEDULED
        )

        db.add(schedule)
        db.commit()
        db.refresh(schedule)

        logger.info(f"✅ Scheduled content {content_id} for {scheduled_dt}")
        return {
            "success": True,
            "schedule_id": schedule.id,
            "scheduled_time": schedule.scheduled_time.isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to schedule content: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}

    finally:
        db.close()
