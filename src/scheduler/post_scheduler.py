"""
Scheduling system for automated Instagram posts
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json

logger = logging.getLogger(__name__)

Base = declarative_base()


class ScheduledPost(Base):
    """Database model for scheduled posts"""
    __tablename__ = 'scheduled_posts'

    id = Column(Integer, primary_key=True)
    job_id = Column(String(100), unique=True, nullable=False)
    post_type = Column(String(20), nullable=False)  # reel, story, carousel, photo, video
    media_path = Column(String(500), nullable=False)
    caption = Column(Text)
    hashtags = Column(Text)  # JSON array
    scheduled_time = Column(DateTime, nullable=False)
    status = Column(String(20), default='scheduled')  # scheduled, posted, failed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    posted_at = Column(DateTime)
    error_message = Column(Text)
    post_metadata = Column(Text)  # JSON for additional data


class PostScheduler:
    """Manage scheduled Instagram posts"""

    def __init__(self, db_path: str, instagram_poster):
        """
        Initialize scheduler

        Args:
            db_path: Path to SQLite database
            instagram_poster: InstagramPoster instance
        """
        self.db_path = db_path
        self.poster = instagram_poster

        # Setup database
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # Setup scheduler
        jobstores = {
            'default': SQLAlchemyJobStore(engine=self.engine)
        }
        self.scheduler = BackgroundScheduler(jobstores=jobstores)
        self.scheduler.start()

        logger.info(f"Scheduler initialized with database: {db_path}")

    def schedule_reel(
        self,
        video_path: Path,
        scheduled_time: datetime,
        caption: str = "",
        hashtags: Optional[List[str]] = None,
        share_to_feed: bool = True
    ) -> str:
        """
        Schedule a reel to be posted

        Args:
            video_path: Path to video file
            scheduled_time: When to post
            caption: Post caption
            hashtags: List of hashtags
            share_to_feed: Also share to feed

        Returns:
            Job ID
        """
        job_id = self._generate_job_id('reel')

        # Create database entry
        post = ScheduledPost(
            job_id=job_id,
            post_type='reel',
            media_path=str(video_path),
            caption=caption,
            hashtags=json.dumps(hashtags) if hashtags else None,
            scheduled_time=scheduled_time,
            post_metadata=json.dumps({'share_to_feed': share_to_feed})
        )
        self.session.add(post)
        self.session.commit()

        # Schedule job
        self.scheduler.add_job(
            func=self._post_reel,
            trigger=DateTrigger(run_date=scheduled_time),
            args=[job_id, video_path, caption, hashtags, share_to_feed],
            id=job_id,
            replace_existing=True
        )

        logger.info(f"Scheduled reel for {scheduled_time}: {video_path.name} (Job ID: {job_id})")
        return job_id

    def schedule_story(
        self,
        media_path: Path,
        scheduled_time: datetime,
        caption: Optional[str] = None,
        mentions: Optional[List[str]] = None,
        link: Optional[str] = None
    ) -> str:
        """Schedule a story to be posted"""
        job_id = self._generate_job_id('story')

        post = ScheduledPost(
            job_id=job_id,
            post_type='story',
            media_path=str(media_path),
            caption=caption,
            scheduled_time=scheduled_time,
            post_metadata=json.dumps({'mentions': mentions, 'link': link})
        )
        self.session.add(post)
        self.session.commit()

        self.scheduler.add_job(
            func=self._post_story,
            trigger=DateTrigger(run_date=scheduled_time),
            args=[job_id, media_path, caption, mentions, link],
            id=job_id,
            replace_existing=True
        )

        logger.info(f"Scheduled story for {scheduled_time} (Job ID: {job_id})")
        return job_id

    def schedule_carousel(
        self,
        media_paths: List[Path],
        scheduled_time: datetime,
        caption: str = "",
        hashtags: Optional[List[str]] = None
    ) -> str:
        """Schedule a carousel to be posted"""
        job_id = self._generate_job_id('carousel')

        post = ScheduledPost(
            job_id=job_id,
            post_type='carousel',
            media_path=json.dumps([str(p) for p in media_paths]),
            caption=caption,
            hashtags=json.dumps(hashtags) if hashtags else None,
            scheduled_time=scheduled_time
        )
        self.session.add(post)
        self.session.commit()

        self.scheduler.add_job(
            func=self._post_carousel,
            trigger=DateTrigger(run_date=scheduled_time),
            args=[job_id, media_paths, caption, hashtags],
            id=job_id,
            replace_existing=True
        )

        logger.info(f"Scheduled carousel for {scheduled_time} (Job ID: {job_id})")
        return job_id

    def schedule_recurring(
        self,
        post_type: str,
        cron_expression: str,
        media_generator: Callable,
        **post_kwargs
    ) -> str:
        """
        Schedule recurring posts using cron expression

        Args:
            post_type: Type of post (reel, story, etc.)
            cron_expression: Cron schedule (e.g., "0 9 * * *" for daily at 9am)
            media_generator: Function that returns media path(s) for each post
            **post_kwargs: Additional arguments for posting

        Returns:
            Job ID
        """
        job_id = self._generate_job_id(f'recurring_{post_type}')

        self.scheduler.add_job(
            func=self._post_recurring,
            trigger=CronTrigger.from_crontab(cron_expression),
            args=[job_id, post_type, media_generator, post_kwargs],
            id=job_id,
            replace_existing=True
        )

        logger.info(f"Scheduled recurring {post_type} with schedule: {cron_expression}")
        return job_id

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled job"""
        try:
            self.scheduler.remove_job(job_id)

            # Update database
            post = self.session.query(ScheduledPost).filter_by(job_id=job_id).first()
            if post:
                post.status = 'cancelled'
                self.session.commit()

            logger.info(f"Cancelled job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False

    def get_scheduled_posts(self, status: Optional[str] = None) -> List[Dict]:
        """
        Get list of scheduled posts

        Args:
            status: Filter by status (scheduled, posted, failed, cancelled)

        Returns:
            List of post dictionaries
        """
        query = self.session.query(ScheduledPost)
        if status:
            query = query.filter_by(status=status)

        posts = query.order_by(ScheduledPost.scheduled_time).all()

        return [
            {
                'job_id': p.job_id,
                'post_type': p.post_type,
                'media_path': p.media_path,
                'caption': p.caption,
                'scheduled_time': p.scheduled_time.isoformat(),
                'status': p.status,
                'created_at': p.created_at.isoformat(),
                'posted_at': p.posted_at.isoformat() if p.posted_at else None,
                'error_message': p.error_message
            }
            for p in posts
        ]

    def get_upcoming_posts(self, hours: int = 24) -> List[Dict]:
        """Get posts scheduled in the next N hours"""
        cutoff = datetime.utcnow() + timedelta(hours=hours)
        posts = self.session.query(ScheduledPost).filter(
            ScheduledPost.scheduled_time <= cutoff,
            ScheduledPost.status == 'scheduled'
        ).order_by(ScheduledPost.scheduled_time).all()

        return [
            {
                'job_id': p.job_id,
                'post_type': p.post_type,
                'media_path': p.media_path,
                'scheduled_time': p.scheduled_time.isoformat(),
                'time_until': str(p.scheduled_time - datetime.utcnow())
            }
            for p in posts
        ]

    def _post_reel(self, job_id: str, video_path: Path, caption: str,
                   hashtags: Optional[List[str]], share_to_feed: bool):
        """Internal method to post reel"""
        try:
            logger.info(f"Posting scheduled reel (Job ID: {job_id})")

            self.poster.post_reel(
                video_path=video_path,
                caption=caption,
                hashtags=hashtags,
                share_to_feed=share_to_feed
            )

            # Update database
            post = self.session.query(ScheduledPost).filter_by(job_id=job_id).first()
            if post:
                post.status = 'posted'
                post.posted_at = datetime.utcnow()
                self.session.commit()

            logger.info(f"Successfully posted reel (Job ID: {job_id})")

        except Exception as e:
            logger.error(f"Failed to post reel (Job ID: {job_id}): {e}")

            # Update database with error
            post = self.session.query(ScheduledPost).filter_by(job_id=job_id).first()
            if post:
                post.status = 'failed'
                post.error_message = str(e)
                self.session.commit()

    def _post_story(self, job_id: str, media_path: Path, caption: Optional[str],
                    mentions: Optional[List[str]], link: Optional[str]):
        """Internal method to post story"""
        try:
            logger.info(f"Posting scheduled story (Job ID: {job_id})")

            self.poster.post_story(
                media_path=media_path,
                caption=caption,
                mentions=mentions,
                link=link
            )

            post = self.session.query(ScheduledPost).filter_by(job_id=job_id).first()
            if post:
                post.status = 'posted'
                post.posted_at = datetime.utcnow()
                self.session.commit()

            logger.info(f"Successfully posted story (Job ID: {job_id})")

        except Exception as e:
            logger.error(f"Failed to post story (Job ID: {job_id}): {e}")

            post = self.session.query(ScheduledPost).filter_by(job_id=job_id).first()
            if post:
                post.status = 'failed'
                post.error_message = str(e)
                self.session.commit()

    def _post_carousel(self, job_id: str, media_paths: List[Path], caption: str,
                       hashtags: Optional[List[str]]):
        """Internal method to post carousel"""
        try:
            logger.info(f"Posting scheduled carousel (Job ID: {job_id})")

            self.poster.post_carousel(
                media_paths=media_paths,
                caption=caption,
                hashtags=hashtags
            )

            post = self.session.query(ScheduledPost).filter_by(job_id=job_id).first()
            if post:
                post.status = 'posted'
                post.posted_at = datetime.utcnow()
                self.session.commit()

            logger.info(f"Successfully posted carousel (Job ID: {job_id})")

        except Exception as e:
            logger.error(f"Failed to post carousel (Job ID: {job_id}): {e}")

            post = self.session.query(ScheduledPost).filter_by(job_id=job_id).first()
            if post:
                post.status = 'failed'
                post.error_message = str(e)
                self.session.commit()

    def _post_recurring(self, job_id: str, post_type: str, media_generator: Callable, kwargs: Dict):
        """Internal method for recurring posts"""
        try:
            media = media_generator()

            if post_type == 'reel':
                self.poster.post_reel(media, **kwargs)
            elif post_type == 'story':
                self.poster.post_story(media, **kwargs)
            # Add more types as needed

            logger.info(f"Posted recurring {post_type} (Job ID: {job_id})")

        except Exception as e:
            logger.error(f"Failed recurring post (Job ID: {job_id}): {e}")

    def _generate_job_id(self, prefix: str) -> str:
        """Generate unique job ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return f"{prefix}_{timestamp}"

    def shutdown(self):
        """Shutdown scheduler"""
        self.scheduler.shutdown()
        self.session.close()
        logger.info("Scheduler shut down")


class SchedulerHelper:
    """Helper utilities for scheduling"""

    @staticmethod
    def parse_natural_time(time_str: str) -> datetime:
        """
        Parse natural language time expressions

        Examples:
            "tomorrow at 9am"
            "in 2 hours"
            "next monday at 3pm"
            "2024-01-15 14:30"
        """
        # This would use a library like dateparser
        # For now, basic implementation
        from dateutil import parser
        return parser.parse(time_str)

    @staticmethod
    def suggest_best_times(timezone: str = 'UTC') -> List[datetime]:
        """
        Suggest optimal posting times based on engagement data

        Returns:
            List of suggested times for the next week
        """
        # This could integrate with Instagram Insights API
        # For now, return common best times
        best_hours = [9, 12, 17, 20]  # 9am, 12pm, 5pm, 8pm

        suggestions = []
        today = datetime.now()

        for day in range(7):
            date = today + timedelta(days=day)
            for hour in best_hours:
                suggestions.append(date.replace(hour=hour, minute=0, second=0, microsecond=0))

        return suggestions[:10]  # Return top 10
