"""
Celery configuration for async training tasks
"""

import os
from celery import Celery
from app.config import settings

# Create Celery instance
celery = Celery(
    "model-trainer",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"]
)

# Configuration
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.train_model": {"queue": "training"},
        "app.tasks.evaluate_model": {"queue": "evaluation"},
        "app.tasks.promote_model": {"queue": "promotion"},
    },
    beat_schedule={
        "sync-training-status": {
            "task": "app.tasks.sync_training_status",
            "schedule": 60.0,  # Every minute
        },
        "cleanup-old-jobs": {
            "task": "app.tasks.cleanup_old_jobs", 
            "schedule": 3600.0,  # Every hour
        },
    },
)

if __name__ == "__main__":
    celery.start()
