"""Celery app — 异步任务队列."""

from celery import Celery

from backend.app.config import settings

celery_app = Celery(
    "fraud_detect",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["backend.app.tasks.batch_tasks", "backend.app.tasks.data_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_soft_time_limit=600,
    task_time_limit=900,
)
