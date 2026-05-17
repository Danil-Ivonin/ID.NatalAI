from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "natalai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    accept_content=["json"],
    result_serializer="json",
    task_serializer="json",
    timezone="UTC",
    task_track_started=True,
)

celery_app.loader.import_task_module("app.workers.tasks")
