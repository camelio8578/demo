"""
Candidate clip endpoints.

GET  /api/v1/videos/{id}/candidates     — list candidates with scores
GET  /api/v1/candidates/{id}            — single candidate with full score breakdown
POST /api/v1/candidates/{id}/score      — trigger rescore
PUT  /api/v1/candidates/{id}/status     — approve / reject
"""
from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models import CandidateClip, ClipScore, SourceVideo
from app.dependencies import get_db
from app.schemas.clips import (
    CandidateClipListOut,
    CandidateClipOut,
    CandidateStatusUpdate,
    RescoreResponse,
)

log = structlog.get_logger(__name__)

router = APIRouter(tags=["clips"])

_VALID_STATUSES = {"candidate", "approved", "rejected", "rendered"}


@router.get(
    "/api/v1/videos/{video_id}/candidates",
    response_model=CandidateClipListOut,
)
def list_candidates(
    video_id: uuid.UUID,
    status: str | None = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
) -> CandidateClipListOut:
    """List all candidate clips for a source video, optionally filtered by status."""
    video = db.query(SourceVideo).filter(SourceVideo.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Source video not found")

    q = db.query(CandidateClip).filter(CandidateClip.source_video_id == video_id)
    if status:
        if status not in _VALID_STATUSES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status '{status}'. Valid: {sorted(_VALID_STATUSES)}",
            )
        q = q.filter(CandidateClip.status == status)

    # Order by best score (join to latest ClipScore)
    clips = q.order_by(CandidateClip.created_at.desc()).all()
    log.info(
        "candidates_listed",
        video_id=str(video_id),
        count=len(clips),
        status_filter=status,
    )
    return CandidateClipListOut(items=clips, total=len(clips))


@router.get(
    "/api/v1/candidates/{candidate_id}",
    response_model=CandidateClipOut,
)
def get_candidate(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> CandidateClip:
    """Get a single candidate clip with its full score breakdown."""
    clip = db.query(CandidateClip).filter(CandidateClip.id == candidate_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Candidate clip not found")
    return clip


@router.post(
    "/api/v1/candidates/{candidate_id}/score",
    response_model=RescoreResponse,
    status_code=202,
)
def rescore_candidate(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> RescoreResponse:
    """Trigger an async rescore job for the candidate clip."""
    clip = db.query(CandidateClip).filter(CandidateClip.id == candidate_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Candidate clip not found")

    video_id = str(clip.source_video_id)
    job_id: str = "sync"

    try:
        from workers.scoring_worker import score_video_candidates

        task = score_video_candidates.delay(video_id)
        job_id = task.id
    except Exception as exc:
        log.warning("rescore_trigger_failed", error=str(exc))

    log.info("rescore_triggered", candidate_id=str(candidate_id), job_id=job_id)
    return RescoreResponse(
        job_id=job_id,
        candidate_clip_id=candidate_id,
        message="Rescore job queued",
    )


@router.put(
    "/api/v1/candidates/{candidate_id}/status",
    response_model=CandidateClipOut,
)
def update_candidate_status(
    candidate_id: uuid.UUID,
    body: CandidateStatusUpdate,
    db: Session = Depends(get_db),
) -> CandidateClip:
    """Approve or reject a candidate clip (human review gate)."""
    clip = db.query(CandidateClip).filter(CandidateClip.id == candidate_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Candidate clip not found")

    if body.status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{body.status}'. Valid: {sorted(_VALID_STATUSES)}",
        )

    old_status = clip.status
    clip.status = body.status
    db.commit()
    db.refresh(clip)

    log.info(
        "candidate_status_updated",
        candidate_id=str(candidate_id),
        old_status=old_status,
        new_status=body.status,
        notes=body.notes,
    )
    return clip
