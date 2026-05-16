"""Publishing job API endpoints.

Routes:
  POST   /api/v1/jobs                     Create publishing job
  GET    /api/v1/jobs                     List jobs (filterable)
  GET    /api/v1/jobs/queue-status        Celery queue depth per queue
  GET    /api/v1/jobs/{id}               Full job + attempts history
  POST   /api/v1/jobs/{id}/retry         Reset to queued, re-enqueue
  DELETE /api/v1/jobs/{id}               Cancel job
  POST   /api/v1/webhooks/ingest         n8n-compatible pipeline trigger
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models import (
    Creator,
    CopyVariant,
    PublishingJob,
    PublishingTarget,
    RenderedAsset,
    SourceVideo,
    Transcript,
)
from app.dependencies import get_db
from app.schemas.publishing import (
    PublishingJobCreate,
    PublishingJobOut,
    QueueCounts,
    QueueStatus,
    WebhookIngestRequest,
    WebhookIngestResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["publishing"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _dispatch_publish(job_id: str) -> str:
    """Fire the publish_job Celery task. Returns Celery task id or fallback."""
    try:
        from workers.publishing_worker import publish_job  # type: ignore

        result = publish_job.delay(publishing_job_id=job_id)
        return result.id
    except Exception as exc:
        logger.warning("celery_dispatch_failed", error=str(exc))
        return f"local-{job_id}"


# ---------------------------------------------------------------------------
# Create Job
# ---------------------------------------------------------------------------


@router.post("/jobs", response_model=PublishingJobOut, status_code=202)
def create_job(body: PublishingJobCreate, db: Session = Depends(get_db)) -> PublishingJob:
    """Create a publishing job and enqueue it for dispatch."""

    # Validate FK references
    asset = db.query(RenderedAsset).filter(RenderedAsset.id == body.rendered_asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="RenderedAsset not found")

    copy = db.query(CopyVariant).filter(CopyVariant.id == body.copy_variant_id).first()
    if not copy:
        raise HTTPException(status_code=404, detail="CopyVariant not found")

    target = (
        db.query(PublishingTarget)
        .filter(PublishingTarget.id == body.publishing_target_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="PublishingTarget not found")

    job = PublishingJob(
        id=uuid.uuid4(),
        rendered_asset_id=body.rendered_asset_id,
        copy_variant_id=body.copy_variant_id,
        publishing_target_id=body.publishing_target_id,
        status="queued",
        scheduled_at=body.scheduled_at,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    task_id = _dispatch_publish(str(job.id))
    logger.info("publishing_job_created", job_id=str(job.id), task_id=task_id)
    return job


# ---------------------------------------------------------------------------
# List Jobs
# ---------------------------------------------------------------------------


@router.get("/jobs", response_model=list[PublishingJobOut])
def list_jobs(
    status: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    creator_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
) -> list[PublishingJob]:
    """List publishing jobs with optional filters."""
    q = db.query(PublishingJob)

    if status:
        q = q.filter(PublishingJob.status == status)

    if platform or creator_id:
        q = q.join(PublishingTarget, PublishingJob.publishing_target_id == PublishingTarget.id)
        if platform:
            q = q.filter(PublishingTarget.platform == platform)
        if creator_id:
            q = q.filter(PublishingTarget.creator_id == creator_id)

    return q.order_by(PublishingJob.created_at.desc()).all()


# ---------------------------------------------------------------------------
# Queue Status — must be before /{id} to avoid routing collision
# ---------------------------------------------------------------------------


@router.get("/jobs/queue-status", response_model=QueueStatus)
def get_queue_status(db: Session = Depends(get_db)) -> QueueStatus:  # noqa: ARG001
    """Return Celery queue depth per worker queue using Celery inspect."""
    counts = QueueCounts()
    active_workers: dict[str, int] = {}

    try:
        from workers.celery_app import app as celery_app  # type: ignore

        inspect = celery_app.control.inspect(timeout=2)
        reserved = inspect.reserved() or {}

        queue_map = {
            "ingestion": 0,
            "transcription": 0,
            "scoring": 0,
            "rendering": 0,
            "publishing": 0,
        }
        for worker_name, tasks in reserved.items():
            active_workers[worker_name] = len(tasks)
            for task in tasks:
                routing_key = task.get("delivery_info", {}).get("routing_key", "")
                if routing_key in queue_map:
                    queue_map[routing_key] += 1

        counts = QueueCounts(**queue_map)
    except Exception as exc:
        logger.warning("celery_inspect_failed", error=str(exc))

    return QueueStatus(queued_jobs=counts, active_workers=active_workers)


# ---------------------------------------------------------------------------
# Get Job
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}", response_model=PublishingJobOut)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> PublishingJob:
    """Get full job details including publish_attempts history."""
    job = db.query(PublishingJob).filter(PublishingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="PublishingJob not found")
    return job


# ---------------------------------------------------------------------------
# Retry Job
# ---------------------------------------------------------------------------


@router.post("/jobs/{job_id}/retry", response_model=PublishingJobOut)
def retry_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> PublishingJob:
    """Reset job to queued status and re-enqueue."""
    job = db.query(PublishingJob).filter(PublishingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="PublishingJob not found")

    if job.status == "published":
        raise HTTPException(status_code=422, detail="Cannot retry an already published job")

    job.status = "queued"
    job.failure_reason = None
    db.commit()
    db.refresh(job)

    task_id = _dispatch_publish(str(job.id))
    logger.info("publishing_job_retried", job_id=str(job_id), task_id=task_id)
    return job


# ---------------------------------------------------------------------------
# Cancel Job
# ---------------------------------------------------------------------------


@router.delete("/jobs/{job_id}", status_code=204)
def cancel_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    """Cancel a queued or failed job."""
    job = db.query(PublishingJob).filter(PublishingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="PublishingJob not found")

    if job.status == "published":
        raise HTTPException(status_code=422, detail="Cannot cancel an already published job")
    if job.status == "in_progress":
        raise HTTPException(
            status_code=422,
            detail="Job is in progress. Wait for it to complete before cancelling.",
        )

    job.status = "cancelled"
    db.commit()
    logger.info("publishing_job_cancelled", job_id=str(job_id))


# ---------------------------------------------------------------------------
# Webhook: n8n-compatible pipeline trigger
# ---------------------------------------------------------------------------


@router.post(
    "/webhooks/ingest",
    response_model=WebhookIngestResponse,
    status_code=202,
    summary="n8n pipeline trigger",
    description="""
## n8n-Compatible Ingest Webhook

Trigger the full ClipOS pipeline from an external automation tool (n8n, Zapier, Make.com, etc.).

### What this does:
1. Creates a `SourceVideo` record for the given URL + creator.
2. Dispatches the ingestion Celery task.
3. If `auto_render=true`, sets a flag so the scoring worker auto-queues rendering.
4. If `auto_publish=true`, sets a flag so the rendering worker auto-queues publishing
   (requires `publishing_target_id`).

### n8n HTTP Request Node settings:
- **Method**: POST
- **URL**: `{API_BASE}/api/v1/webhooks/ingest`
- **Body Content-Type**: JSON
- **Body**:
```json
{
  "source_url": "https://youtube.com/watch?v=...",
  "creator_id": "uuid-here",
  "auto_render": true,
  "auto_publish": false
}
```

### Notes:
- Returns 409 if the video URL already exists for this creator (use `force_redownload=true` to override).
- `auto_publish=true` without `publishing_target_id` returns 422.
""",
)
def webhook_ingest(body: WebhookIngestRequest, db: Session = Depends(get_db)) -> WebhookIngestResponse:
    """n8n-compatible entry point to trigger the full ClipOS pipeline."""

    if body.auto_publish and not body.publishing_target_id:
        raise HTTPException(
            status_code=422,
            detail="auto_publish=true requires publishing_target_id",
        )

    creator = db.query(Creator).filter(Creator.id == body.creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    # Check for existing video
    existing = (
        db.query(SourceVideo)
        .filter(
            SourceVideo.source_url == body.source_url,
            SourceVideo.creator_id == body.creator_id,
        )
        .first()
    )
    if existing and not body.force_redownload:
        raise HTTPException(
            status_code=409,
            detail=f"Video already ingested with id={existing.id}. Use force_redownload=true to re-queue.",
        )

    video = SourceVideo(
        id=uuid.uuid4(),
        creator_id=body.creator_id,
        source_url=body.source_url,
        status="discovered",
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    pipeline_flags = {
        "auto_render": body.auto_render,
        "auto_publish": body.auto_publish,
        "publishing_target_id": str(body.publishing_target_id) if body.publishing_target_id else None,
    }

    try:
        from workers.ingestion_worker import ingest_video_task  # type: ignore

        result = ingest_video_task.apply_async(
            kwargs={
                "source_url": body.source_url,
                "creator_id": str(body.creator_id),
                "source_video_id": str(video.id),
            },
            headers={"pipeline_flags": pipeline_flags},
        )
        job_id = result.id
    except Exception as exc:
        logger.warning("webhook_celery_dispatch_failed", error=str(exc))
        job_id = f"local-{video.id}"

    logger.info(
        "webhook_ingest_queued",
        video_id=str(video.id),
        job_id=job_id,
        pipeline_flags=pipeline_flags,
    )

    return WebhookIngestResponse(
        job_id=job_id,
        source_video_id=video.id,
        message="Pipeline triggered via webhook",
        pipeline_flags=pipeline_flags,
    )
