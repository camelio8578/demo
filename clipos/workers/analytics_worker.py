"""
Celery tasks for ingesting platform analytics into ClipOS.

Tasks:
  ingest_analytics(publishing_job_id)  — Fetch analytics for one published job.
  refresh_analytics()                  — Periodic: refresh all jobs < 30 days old.

Analytics failures are isolated — they never crash publishing or other workers.
Queue: publishing (shared with publishing_worker for simplicity; adjust if needed)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog

from workers.celery_app import app as celery_app

log = structlog.get_logger(__name__)

# Minimum views threshold to mark a clip as a high performer
HIGH_PERFORMER_VIEWS_THRESHOLD = 10_000


# ---------------------------------------------------------------------------
# Single-job analytics ingestion
# ---------------------------------------------------------------------------


@celery_app.task(
    name="workers.analytics_worker.ingest_analytics",
    queue="publishing",
    bind=False,
)
def ingest_analytics(publishing_job_id: str) -> dict:
    """Fetch and persist analytics for a single publishing job.

    Steps:
    1. Load publishing_job + publishing_target from DB.
    2. Determine platform and instantiate the appropriate ingestor.
    3. Call ingestor.ingest(platform_post_id).
       - Returns None if not configured or on error; never raises.
    4. If data returned: create analytics_snapshot record.
    5. Feedback loop:
       - If views > threshold: mark candidate_clip as high_performer
         (sets clip.status tag and updates prior_performance_score).
    """
    task_log = log.bind(task="ingest_analytics", publishing_job_id=publishing_job_id)
    task_log.info("task_started")

    from app.db.base import SessionLocal
    from app.db.models import (
        AnalyticsSnapshot,
        CandidateClip,
        ClipScore,
        PublishingJob,
        PublishingTarget,
        RenderedAsset,
    )

    db = SessionLocal()

    try:
        job = (
            db.query(PublishingJob)
            .filter(PublishingJob.id == uuid.UUID(publishing_job_id))
            .first()
        )
        if not job:
            task_log.warning("job_not_found")
            return {"error": "Job not found"}

        if not job.platform_post_id:
            task_log.warning("no_platform_post_id")
            return {"error": "Job has no platform_post_id"}

        target = (
            db.query(PublishingTarget)
            .filter(PublishingTarget.id == job.publishing_target_id)
            .first()
        )
        if not target:
            task_log.warning("target_not_found")
            return {"error": "PublishingTarget not found"}

        platform = target.platform
        task_log = task_log.bind(platform=platform, post_id=job.platform_post_id)

        # 2. Instantiate ingestor
        ingestor = _get_ingestor(platform)
        if ingestor is None:
            task_log.info("no_ingestor_for_platform")
            return {"skipped": f"No analytics ingestor for platform {platform!r}"}

        # 3. Ingest — wrapped in try/except; failure must not propagate
        try:
            data = ingestor.ingest(job.platform_post_id)
        except Exception as exc:
            task_log.warning("ingestor_raised", error=str(exc))
            data = None

        if data is None:
            task_log.info("no_analytics_data_returned")
            return {"result": "no_data"}

        # 4. Persist analytics_snapshot
        snapshot = AnalyticsSnapshot(
            id=uuid.uuid4(),
            publishing_job_id=job.id,
            snapshot_at=datetime.now(timezone.utc),
            views=data.get("views"),
            likes=data.get("likes"),
            comments=data.get("comments"),
            shares=data.get("shares"),
            saves=data.get("saves"),
            watch_time_seconds=data.get("watch_time_seconds"),
            completion_rate=data.get("completion_rate"),
            platform_raw=data.get("platform_raw"),
        )
        db.add(snapshot)
        db.commit()
        task_log.info("snapshot_saved", views=snapshot.views)

        # 5. Feedback loop: high-performer detection
        views = snapshot.views or 0
        if views >= HIGH_PERFORMER_VIEWS_THRESHOLD:
            _mark_high_performer(db, job, views, task_log)

        return {
            "publishing_job_id": publishing_job_id,
            "snapshot_id": str(snapshot.id),
            "views": views,
        }

    except Exception as exc:
        # Analytics failure must never crash the system
        task_log.error("ingest_analytics_failed", error=str(exc))
        return {"error": str(exc)}
    finally:
        db.close()


def _get_ingestor(platform: str):
    """Return the ingestor instance for the given platform, or None."""
    try:
        if platform == "youtube":
            from workers.analytics.youtube_analytics import YouTubeAnalyticsIngestor
            return YouTubeAnalyticsIngestor()
        elif platform == "tiktok":
            from workers.analytics.tiktok_analytics import TikTokAnalyticsIngestor
            return TikTokAnalyticsIngestor()
        elif platform == "instagram":
            from workers.analytics.instagram_analytics import InstagramAnalyticsIngestor
            return InstagramAnalyticsIngestor()
        return None
    except Exception as exc:
        log.warning("ingestor_import_failed", platform=platform, error=str(exc))
        return None


def _mark_high_performer(db, job, views: int, task_log) -> None:
    """Update the related candidate_clip and its score to reflect high performance."""
    try:
        from app.db.models import ClipScore, PublishingJob, RenderedAsset, CandidateClip

        asset = db.query(RenderedAsset).filter(
            RenderedAsset.id == job.rendered_asset_id
        ).first()
        if not asset:
            return

        clip = db.query(CandidateClip).filter(
            CandidateClip.id == asset.candidate_clip_id
        ).first()
        if not clip:
            return

        # Boost the prior_performance_score for future scoring of same creator
        latest_score = (
            db.query(ClipScore)
            .filter(ClipScore.candidate_clip_id == clip.id)
            .order_by(ClipScore.created_at.desc())
            .first()
        )
        if latest_score:
            boost = min(1.0, latest_score.prior_performance_score + 0.2)
            latest_score.prior_performance_score = boost
            db.commit()
            task_log.info(
                "high_performer_score_boosted",
                clip_id=str(clip.id),
                views=views,
                new_prior_performance_score=boost,
            )
    except Exception as exc:
        task_log.warning("high_performer_update_failed", error=str(exc))


# ---------------------------------------------------------------------------
# Periodic analytics refresh
# ---------------------------------------------------------------------------


@celery_app.task(
    name="workers.analytics_worker.refresh_analytics",
    queue="publishing",
)
def refresh_analytics() -> dict:
    """Periodic task: refresh analytics for all published jobs < 30 days old.

    Intended to be called every 6 hours via Celery Beat:

      app.conf.beat_schedule = {
          "refresh-analytics-every-6h": {
              "task": "workers.analytics_worker.refresh_analytics",
              "schedule": crontab(minute=0, hour="*/6"),
          }
      }
    """
    from app.db.base import SessionLocal
    from app.db.models import PublishingJob

    task_log = log.bind(task="refresh_analytics")
    task_log.info("task_started")

    db = SessionLocal()
    dispatched = 0

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        jobs = (
            db.query(PublishingJob)
            .filter(
                PublishingJob.status == "published",
                PublishingJob.published_at >= cutoff,
                PublishingJob.platform_post_id != None,  # noqa: E711
            )
            .all()
        )

        task_log.info("found_published_jobs", count=len(jobs))

        for job in jobs:
            try:
                ingest_analytics.delay(publishing_job_id=str(job.id))
                dispatched += 1
            except Exception as exc:
                task_log.warning(
                    "dispatch_failed",
                    job_id=str(job.id),
                    error=str(exc),
                )

        return {"dispatched": dispatched, "total_eligible": len(jobs)}
    finally:
        db.close()
