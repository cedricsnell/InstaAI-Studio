"""
Celery tasks for automated content generation
"""
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

from .celery_app import celery_app
from ..database.database import SessionLocal
from ..database.models import (
    User, InstagramAccount, InstagramPost, GeneratedContent, ContentStatus
)
from ..ai.content_repurposer import ContentRepurposer
from ..video_processor.repurposer import VideoRepurposer

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="src.tasks.content_tasks.generate_reels_for_account")
def generate_reels_for_account(self, account_id: int, count: int = 10) -> Dict[str, Any]:
    """
    Generate reel ideas for a specific account.

    Args:
        account_id: Instagram account ID
        count: Number of reels to generate

    Returns:
        {" success": bool, "reels_generated": int, "account_id": int}
    """
    db = SessionLocal()

    try:
        logger.info(f"Generating {count} reels for account {account_id}")

        # Get account
        account = db.query(InstagramAccount).filter(
            InstagramAccount.id == account_id,
            InstagramAccount.is_active == True
        ).first()

        if not account:
            logger.error(f"Account {account_id} not found")
            return {"success": False, "error": "Account not found"}

        # Get posts
        posts = db.query(InstagramPost).filter(
            InstagramPost.instagram_account_id == account_id
        ).order_by(InstagramPost.engagement_rate.desc()).limit(100).all()

        if not posts:
            logger.warning(f"No posts found for account {account_id}")
            return {"success": False, "error": "No posts available"}

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

        # Generate reel ideas
        repurposer = ContentRepurposer()
        analysis = repurposer.analyze_top_performing_posts(posts_data[:20])
        reel_ideas = repurposer.generate_reel_ideas(
            source_posts=posts_data,
            analysis=analysis,
            count=count
        )

        # Save to database
        for reel in reel_ideas:
            content = GeneratedContent(
                user_id=account.user_id,
                instagram_account_id=account_id,
                content_type="reel",
                title=reel.get("title", "Untitled Reel"),
                description=reel.get("script", ""),
                suggested_caption=reel.get("caption", ""),
                generation_config=reel,
                status=ContentStatus.READY,
            )
            db.add(content)

        db.commit()

        logger.info(f"✅ Generated {len(reel_ideas)} reels for account {account_id}")
        return {
            "success": True,
            "reels_generated": len(reel_ideas),
            "account_id": account_id
        }

    except Exception as e:
        logger.error(f"Failed to generate reels: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}

    finally:
        db.close()


@celery_app.task(bind=True, name="src.tasks.content_tasks.generate_daily_content_batch")
def generate_daily_content_batch(self) -> Dict[str, Any]:
    """
    Generate content for all active accounts (scheduled daily).

    Returns:
        Summary of content generation
    """
    db = SessionLocal()

    try:
        logger.info("Starting daily content generation batch")

        # Get all active accounts
        accounts = db.query(InstagramAccount).filter(
            InstagramAccount.is_active == True
        ).all()

        results = []
        for account in accounts:
            try:
                # Generate 5 reels per account daily
                result = generate_reels_for_account.delay(account.id, count=5)
                results.append({
                    "account_id": account.id,
                    "task_id": result.id,
                    "username": account.username
                })
            except Exception as e:
                logger.error(f"Failed to queue generation for account {account.id}: {e}")

        logger.info(f"✅ Queued content generation for {len(results)} accounts")
        return {
            "success": True,
            "accounts_processed": len(results),
            "tasks_queued": results
        }

    except Exception as e:
        logger.error(f"Daily content batch failed: {e}")
        return {"success": False, "error": str(e)}

    finally:
        db.close()


@celery_app.task(bind=True, name="src.tasks.content_tasks.create_video_from_reel_plan")
def create_video_from_reel_plan(
    self, reel_plan: Dict[str, Any], source_posts: List[Dict], niche: str = "General"
) -> Dict[str, Any]:
    """
    Create actual video file from reel plan (long-running task).

    Args:
        reel_plan: AI-generated reel concept
        source_posts: Available posts with media URLs
        niche: Content niche

    Returns:
        {"success": bool, "video_path": str, "duration": float}
    """
    try:
        logger.info(f"Creating video: {reel_plan.get('title')}")

        repurposer = VideoRepurposer()

        # Create reel (this is async in the original, but Celery handles that)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        video_path = loop.run_until_complete(
            repurposer.create_reel_from_plan(reel_plan, source_posts, niche)
        )

        if not video_path:
            return {"success": False, "error": "Video creation failed"}

        logger.info(f"✅ Video created: {video_path}")
        return {
            "success": True,
            "video_path": str(video_path),
            "filename": video_path.name
        }

    except Exception as e:
        logger.error(f"Video creation failed: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task(bind=True, name="src.tasks.content_tasks.analyze_account_performance")
def analyze_account_performance(self, account_id: int) -> Dict[str, Any]:
    """
    Run performance analysis on account.

    Args:
        account_id: Instagram account ID

    Returns:
        Analysis results
    """
    db = SessionLocal()

    try:
        logger.info(f"Analyzing performance for account {account_id}")

        account = db.query(InstagramAccount).filter(
            InstagramAccount.id == account_id
        ).first()

        if not account:
            return {"success": False, "error": "Account not found"}

        posts = db.query(InstagramPost).filter(
            InstagramPost.instagram_account_id == account_id
        ).order_by(InstagramPost.engagement_rate.desc()).limit(50).all()

        if not posts:
            return {"success": False, "error": "No posts to analyze"}

        posts_data = [
            {
                "media_type": p.media_type,
                "caption": p.caption,
                "engagement_rate": p.engagement_rate,
                "likes_count": p.likes_count,
                "comments_count": p.comments_count,
                "saves_count": p.saves_count,
                "timestamp": p.timestamp,
            }
            for p in posts
        ]

        repurposer = ContentRepurposer()
        analysis = repurposer.analyze_top_performing_posts(posts_data)

        logger.info(f"✅ Analysis complete for account {account_id}")
        return {
            "success": True,
            "account_id": account_id,
            "analysis": analysis
        }

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return {"success": False, "error": str(e)}

    finally:
        db.close()
