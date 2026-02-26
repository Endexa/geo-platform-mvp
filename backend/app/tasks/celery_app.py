from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "geo_platform",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="geo_platform",
    task_routes={
        "app.tasks.audit.*": {"queue": "audit"},
        "app.tasks.analysis.*": {"queue": "analysis"},
    },
    include=["app.tasks.audit_tasks", "app.tasks.code_analysis_tasks"],
)
