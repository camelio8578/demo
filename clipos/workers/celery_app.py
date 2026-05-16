"""Celery application instance."""

import os

from celery import Celery

app = Celery(
    "clipos",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

app.conf.task_routes = {
    "workers.ingestion_worker.*": {"queue": "ingestion"},
    "workers.transcription_worker.*": {"queue": "transcription"},
    "workers.scoring_worker.*": {"queue": "scoring"},
    "workers.rendering_worker.*": {"queue": "rendering"},
    "workers.publishing_worker.*": {"queue": "publishing"},
}

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)
