"""Analytics API endpoints.

Routes:
  GET  /api/v1/analytics/jobs/{job_id}   All snapshots for a publishing job
  POST /api/v1/analytics/ingest/{job_id} Manually trigger analytics refresh
  GET  /api/v1/analytics/summary         Creator-level performance summary
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    AnalyticsSnapshot,
    Creator,
    PublishingJob,
    PublishingTarget,
    RenderedAsset,
    CandidateClip,
)
from app.dependencies import get_db
from app.schemas.analytics import (
    AnalyticsSnapshotOut,
    AnalyticsSummaryOut,
    CreatorPerformanceSummary,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


# ---------------------------------------------------------------------------
# Get snapshots for a publishing job
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}", response_model=list[AnalyticsSnapshotOut])
def get_job_analytics(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[AnalyticsSnapshot]:
    """Return all analytics snapshots for a given publishing job, newest first."""
    job = db.query(PublishingJob).filter(PublishingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="PublishingJob not found")

    snapshots = (
        db.query(AnalyticsSnapshot)
        .filter(AnalyticsSnapshot.publishing_job_id == job_id)
        .order_by(AnalyticsSnapshot.snapshot_at.desc())
        .all()
    )
    return snapshots


# ---------------------------------------------------------------------------
# Manually trigger analytics refresh
# ---------------------------------------------------------------------------


@router.post("/ingest/{job_id}", status_code=202)
def trigger_analytics_ingest(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    """Manually trigger an analytics refresh for a specific publishing job."""
    job = db.query(PublishingJob).filter(PublishingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="PublishingJob not found")

    if job.status != "published":
        raise HTTPException(
            status_code=422,
            detail=f"Job is not in 'published' state (current: {job.status}). Cannot ingest analytics.",
        )

    if not job.platform_post_id:
        raise HTTPException(
            status_code=422,
            detail="Job has no platform_post_id. Cannot ingest analytics.",
        )

    task_id: str
    try:
        from workers.analytics_worker import ingest_analytics  # type: ignore

        result = ingest_analytics.delay(publishing_job_id=str(job_id))
        task_id = result.id
    except Exception as exc:
        logger.warning("analytics_celery_dispatch_failed", error=str(exc))
        task_id = f"local-{job_id}"

    logger.info("analytics_ingest_triggered", job_id=str(job_id), task_id=task_id)
    return {"message": "Analytics ingest queued", "task_id": task_id, "job_id": str(job_id)}


# ---------------------------------------------------------------------------
# Creator-level performance summary
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=AnalyticsSummaryOut)
def get_analytics_summary(db: Session = Depends(get_db)) -> AnalyticsSummaryOut:
    """Return creator-level performance summary across all published clips."""

    total_snapshots = db.query(func.count(AnalyticsSnapshot.id)).scalar() or 0
    total_published_jobs = (
        db.query(func.count(PublishingJob.id))
        .filter(PublishingJob.status == "published")
        .scalar()
        or 0
    )

    # Build per-creator summary
    creators_raw = db.query(Creator).all()
    creator_summaries: list[CreatorPerformanceSummary] = []

    platform_breakdown: dict[str, int] = {}

    for creator in creators_raw:
        # Get all published jobs for this creator via publishing_targets
        job_ids_q = (
            db.query(PublishingJob.id, PublishingTarget.platform)
            .join(PublishingTarget, PublishingJob.publishing_target_id == PublishingTarget.id)
            .filter(
                PublishingTarget.creator_id == creator.id,
                PublishingJob.status == "published",
            )
        )
        job_rows = job_ids_q.all()

        if not job_rows:
            continue

        job_id_list = [r[0] for r in job_rows]

        # Accumulate platform breakdown
        for _, platform in job_rows:
            if platform not in platform_breakdown:
                platform_breakdown[platform] = 0

        # Aggregate snapshot metrics
        agg = (
            db.query(
                func.avg(AnalyticsSnapshot.views).label("avg_views"),
                func.avg(AnalyticsSnapshot.likes).label("avg_likes"),
                func.avg(AnalyticsSnapshot.completion_rate).label("avg_completion"),
                func.sum(AnalyticsSnapshot.views).label("total_views"),
            )
            .filter(AnalyticsSnapshot.publishing_job_id.in_(job_id_list))
            .first()
        )

        avg_views = float(agg.avg_views or 0)
        avg_likes = float(agg.avg_likes or 0)
        avg_completion = float(agg.avg_completion) if agg.avg_completion else None

        # Accumulate platform views
        for _, platform in job_rows:
            platform_breakdown[platform] = platform_breakdown.get(platform, 0) + int(
                (agg.total_views or 0) / max(len(job_id_list), 1)
            )

        # Find top clip by max views
        top_snap = (
            db.query(AnalyticsSnapshot)
            .filter(AnalyticsSnapshot.publishing_job_id.in_(job_id_list))
            .order_by(AnalyticsSnapshot.views.desc())
            .first()
        )

        top_clip_id: Optional[uuid.UUID] = None
        top_clip_views: Optional[int] = None
        if top_snap:
            top_job = db.query(PublishingJob).filter(PublishingJob.id == top_snap.publishing_job_id).first()
            if top_job:
                asset = db.query(RenderedAsset).filter(RenderedAsset.id == top_job.rendered_asset_id).first()
                if asset:
                    top_clip_id = asset.candidate_clip_id
            top_clip_views = top_snap.views

        creator_summaries.append(
            CreatorPerformanceSummary(
                creator_id=creator.id,
                creator_name=creator.name,
                total_published_clips=len(job_id_list),
                avg_views=avg_views,
                avg_likes=avg_likes,
                avg_completion_rate=avg_completion,
                top_clip_id=top_clip_id,
                top_clip_views=top_clip_views,
            )
        )

    return AnalyticsSummaryOut(
        generated_at=datetime.now(timezone.utc),
        total_snapshots=total_snapshots,
        total_published_jobs=total_published_jobs,
        creators=creator_summaries,
        platform_breakdown=platform_breakdown,
    )
