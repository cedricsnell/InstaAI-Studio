"""
Celery configuration for async task processing
"""
from celery import Celery
from celery.schedules import crontab
import os

# Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "instaai",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "src.tasks.content_tasks",
        "src.tasks.instagram_tasks",
        "src.tasks.scheduling_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
    },

    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=1800,  # 30 minutes max
    task_soft_time_limit=1500,  # 25 minutes soft limit

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,

    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,

    # Beat schedule for periodic tasks
    beat_schedule={
        # Sync media every 6 hours
        "sync-all-accounts-media": {
            "task": "src.tasks.instagram_tasks.sync_all_accounts",
            "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
        },

        # Generate content daily at 9 AM
        "generate-daily-content": {
            "task": "src.tasks.content_tasks.generate_daily_content_batch",
            "schedule": crontab(minute=0, hour=9),  # 9 AM daily
        },

        # Check scheduled posts every 5 minutes
        "process-scheduled-posts": {
            "task": "src.tasks.scheduling_tasks.process_pending_posts",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },

        # Refresh Instagram tokens weekly
        "refresh-tokens": {
            "task": "src.tasks.instagram_tasks.refresh_expiring_tokens",
            "schedule": crontab(minute=0, hour=0, day_of_week=1),  # Monday midnight
        },
    },
)

# Optional: Configure logging
celery_app.conf.update(
    worker_hijack_root_logger=False,
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s"
)
