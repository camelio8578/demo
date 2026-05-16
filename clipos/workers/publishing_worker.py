"""
Celery tasks for publishing ClipOS clips to social platforms.

Tasks:
  publish_job(publishing_job_id)  — Publish one job via the appropriate adapter.
  process_publishing_queue()      — Periodic task: dispatch queued jobs whose
                                    scheduled_at <= now.

Queue: publishing
Retry policy: up to 3 attempts with exponential back-off (60s, 120s, 240s).
              NOT retried for configuration errors (missing credentials).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import structlog

from workers.celery_app import app as celery_app

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Main publish task
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="workers.publishing_worker.publish_job",
    queue="publishing",
    max_retries=3,
)
def publish_job(self, publishing_job_id: str) -> dict:
    """Publish a single publishing_job to its target platform.

    Steps:
    1. Load publishing_job from DB with related asset, copy_variant, target.
    2. Update status → in_progress.
    3. Create a publish_attempt record.
    4. Obtain the correct publishing adapter.
    5. Check adapter.is_configured():
       - If not configured: mark job failed with clear message. DO NOT retry.
    6. Call adapter.upload_video(...).
    7. On success: status → published, save platform_post_id + published_at.
    8. On transient failure: status → failed, increment retry_count.
       - If retry_count < 3: re-queue with exponential back-off.
    9. Update publish_attempt with outcome.
    """
    task_log = log.bind(task="publish_job", publishing_job_id=publishing_job_id)
    task_log.info("task_started")

    from app.db.base import SessionLocal
    from app.db.models import (
        PublishAttempt,
        PublishingJob,
        PublishingTarget,
        RenderedAsset,
        CopyVariant,
    )
    from workers.publishing.adapter_factory import get_adapter

    db = SessionLocal()
    attempt_id: str | None = None

    try:
        # 1. Load job
        job = (
            db.query(PublishingJob)
            .filter(PublishingJob.id == uuid.UUID(publishing_job_id))
            .first()
        )
        if not job:
            task_log.error("job_not_found")
            return {"error": f"PublishingJob {publishing_job_id} not found"}

        asset = (
            db.query(RenderedAsset)
            .filter(RenderedAsset.id == job.rendered_asset_id)
            .first()
        )
        copy = (
            db.query(CopyVariant)
            .filter(CopyVariant.id == job.copy_variant_id)
            .first()
        )
        target = (
            db.query(PublishingTarget)
            .filter(PublishingTarget.id == job.publishing_target_id)
            .first()
        )

        if not asset or not copy or not target:
            job.status = "failed"
            job.failure_reason = "Related asset, copy_variant, or publishing_target not found."
            db.commit()
            return {"error": "Missing related records"}

        # 2. Mark in_progress
        job.status = "in_progress"
        db.commit()

        # 3. Create attempt record
        attempt_number = len(job.publish_attempts) + 1
        attempt = PublishAttempt(
            id=uuid.uuid4(),
            publishing_job_id=job.id,
            attempt_number=attempt_number,
            attempted_at=datetime.now(timezone.utc),
            status="failed",  # will be updated on success
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        attempt_id = str(attempt.id)
        task_log = task_log.bind(attempt_id=attempt_id, platform=target.platform)

        # 4. Get adapter
        try:
            adapter = get_adapter(target.platform)
        except ValueError as ve:
            job.status = "failed"
            job.failure_reason = str(ve)
            attempt.status = "failed"
            attempt.failure_reason = str(ve)
            db.commit()
            task_log.error("unknown_platform", error=str(ve))
            return {"error": str(ve)}

        # 5. Check configuration
        is_configured = asyncio.get_event_loop().run_until_complete(
            adapter.is_configured()
        )
        if not is_configured:
            msg = (
                f"Platform adapter '{target.platform}' is not configured. "
                "Set the required environment variables and retry manually. "
                "See docs/credential-checklist.md."
            )
            job.status = "failed"
            job.failure_reason = msg
            attempt.status = "failed"
            attempt.failure_reason = msg
            db.commit()
            task_log.error("adapter_not_configured", platform=target.platform)
            # DO NOT retry — this is a configuration error, not transient
            return {"error": msg}

        # 6. Upload
        hashtags: list[str] = copy.hashtags or []
        task_log.info(
            "uploading",
            asset_path=asset.output_path,
            platform=target.platform,
        )

        result = asyncio.get_event_loop().run_until_complete(
            adapter.upload_video(
                video_path=asset.output_path or "",
                thumbnail_path=asset.thumbnail_path,
                title=copy.title or "",
                caption=copy.caption or "",
                hashtags=hashtags,
            )
        )

        # 7. Handle result
        if result.success:
            job.status = "published"
            job.platform_post_id = result.platform_post_id
            job.published_at = datetime.now(timezone.utc)
            attempt.status = "success"
            attempt.response_body = str(result.response_data)
            db.commit()
            task_log.info(
                "published",
                platform_post_id=result.platform_post_id,
            )
            return {
                "publishing_job_id": publishing_job_id,
                "platform_post_id": result.platform_post_id,
                "status": "published",
            }
        else:
            raise RuntimeError(result.error_message or "Unknown upload error")

    except Exception as exc:
        task_log.error("publish_failed", error=str(exc))

        if attempt_id:
            try:
                from app.db.models import PublishAttempt as PA

                atmp = db.query(PA).filter(PA.id == uuid.UUID(attempt_id)).first()
                if atmp:
                    atmp.status = "failed"
                    atmp.failure_reason = str(exc)
                    db.commit()
            except Exception as db_exc:
                task_log.error("failed_to_update_attempt", error=str(db_exc))

        try:
            from app.db.models import PublishingJob as PJ

            j = db.query(PJ).filter(PJ.id == uuid.UUID(publishing_job_id)).first()
            if j:
                j.status = "failed"
                j.failure_reason = str(exc)
                j.retry_count = (j.retry_count or 0) + 1
                db.commit()

                retry_count = j.retry_count
                if retry_count < 3:
                    countdown = 60 * (2 ** (retry_count - 1))  # 60s, 120s, 240s
                    task_log.info(
                        "scheduling_retry",
                        retry=retry_count,
                        countdown=countdown,
                    )
                    raise self.retry(exc=exc, countdown=countdown)
        except self.MaxRetriesExceededError:
            task_log.error("max_retries_exceeded")
        except Exception as retry_exc:
            task_log.error("retry_scheduling_failed", error=str(retry_exc))

        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Periodic queue processing task
# ---------------------------------------------------------------------------


@celery_app.task(
    name="workers.publishing_worker.process_publishing_queue",
    queue="publishing",
)
def process_publishing_queue() -> dict:
    """Periodic task: find queued jobs with scheduled_at <= now and dispatch them.

    This task is intended to be called every 30 seconds via Celery Beat.
    Configure in celery_app.conf.beat_schedule.
    """
    from app.db.base import SessionLocal
    from app.db.models import PublishingJob

    task_log = log.bind(task="process_publishing_queue")
    task_log.info("task_started")

    db = SessionLocal()
    dispatched = 0

    try:
        now = datetime.now(timezone.utc)
        # Jobs that are queued and either have no scheduled_at or it's in the past
        pending = (
            db.query(PublishingJob)
            .filter(
                PublishingJob.status == "queued",
                (PublishingJob.scheduled_at == None)  # noqa: E711
                | (PublishingJob.scheduled_at <= now),
            )
            .all()
        )

        task_log.info("found_pending_jobs", count=len(pending))

        for job in pending:
            try:
                publish_job.delay(publishing_job_id=str(job.id))
                dispatched += 1
                task_log.info("dispatched", job_id=str(job.id))
            except Exception as dispatch_exc:
                task_log.error(
                    "dispatch_failed",
                    job_id=str(job.id),
                    error=str(dispatch_exc),
                )

        return {"dispatched": dispatched, "found": len(pending)}
    finally:
        db.close()
