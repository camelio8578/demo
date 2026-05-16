"""Review queue and task management endpoints.

Routes:
  GET  /api/v1/review/queue          Candidate clips awaiting review (sorted by score)
  POST /api/v1/review/tasks          Create a user_review_task for a candidate
  GET  /api/v1/review/tasks          List review tasks with optional filters
  PUT  /api/v1/review/tasks/{id}     Update task status (approved/rejected/escalated)
"""

from __future__ import annotations

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models import (
    CandidateClip,
    ClipScore,
    UserReviewTask,
)
from app.dependencies import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/review", tags=["review"])


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------


@router.get("/queue")
def get_review_queue(
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return all candidate_clips with status=candidate or approved, sorted by score DESC.

    Each item includes:
    - candidate_clip fields
    - scores list
    - source_video_id for navigation
    """
    clips = (
        db.query(CandidateClip)
        .filter(CandidateClip.status.in_(["candidate", "approved"]))
        .all()
    )

    # Sort by latest total_score descending (clips without a score go last)
    def _best_score(clip: CandidateClip) -> float:
        if not clip.scores:
            return -1.0
        return max(s.total_score for s in clip.scores)

    clips_sorted = sorted(clips, key=_best_score, reverse=True)

    result = []
    for clip in clips_sorted:
        score_data = None
        if clip.scores:
            latest = max(clip.scores, key=lambda s: s.created_at)
            score_data = {
                "id": str(latest.id),
                "total_score": latest.total_score,
                "speech_density": latest.speech_density,
                "sentiment_score": latest.sentiment_score,
                "hook_phrase_score": latest.hook_phrase_score,
                "pause_burst_score": latest.pause_burst_score,
                "novelty_score": latest.novelty_score,
                "completeness_score": latest.completeness_score,
                "duration_fit_score": latest.duration_fit_score,
                "risk_flag_score": latest.risk_flag_score,
                "prior_performance_score": latest.prior_performance_score,
                "llm_rescore": latest.llm_rescore,
                "scoring_version": latest.scoring_version,
            }

        result.append(
            {
                "id": str(clip.id),
                "source_video_id": str(clip.source_video_id),
                "transcript_id": str(clip.transcript_id) if clip.transcript_id else None,
                "start_time": clip.start_time,
                "end_time": clip.end_time,
                "duration_seconds": clip.duration_seconds,
                "segment_text": clip.segment_text,
                "status": clip.status,
                "created_at": clip.created_at.isoformat(),
                "updated_at": clip.updated_at.isoformat(),
                "score": score_data,
                "rendered_assets": [
                    {"id": str(a.id), "status": a.status}
                    for a in (clip.rendered_assets or [])
                ],
            }
        )

    return result


# ---------------------------------------------------------------------------
# Create review task
# ---------------------------------------------------------------------------


@router.post("/tasks", status_code=201)
def create_review_task(
    body: dict,
    db: Session = Depends(get_db),
) -> dict:
    """Create a user_review_task for a candidate clip.

    Body:
      candidate_clip_id (uuid, required)
      task_type (str, default: "review_clip")
      assigned_to (str, optional)
      notes (str, optional)
    """
    clip_id_raw = body.get("candidate_clip_id")
    if not clip_id_raw:
        raise HTTPException(status_code=422, detail="candidate_clip_id is required")

    try:
        clip_id = uuid.UUID(str(clip_id_raw))
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid candidate_clip_id UUID")

    clip = db.query(CandidateClip).filter(CandidateClip.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="CandidateClip not found")

    task_type = body.get("task_type", "review_clip")
    valid_types = {"review_clip", "approve_copy", "review_flag", "manual_check"}
    if task_type not in valid_types:
        raise HTTPException(
            status_code=422,
            detail=f"task_type must be one of {sorted(valid_types)}",
        )

    task = UserReviewTask(
        id=uuid.uuid4(),
        task_type=task_type,
        candidate_clip_id=clip_id,
        assigned_to=body.get("assigned_to"),
        status="pending",
        notes=body.get("notes"),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    logger.info("review_task_created", task_id=str(task.id), clip_id=str(clip_id))
    return _task_to_dict(task)


# ---------------------------------------------------------------------------
# List review tasks
# ---------------------------------------------------------------------------


@router.get("/tasks")
def list_review_tasks(
    status: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List user_review_tasks with optional filters."""
    q = db.query(UserReviewTask)

    if status:
        q = q.filter(UserReviewTask.status == status)
    if task_type:
        q = q.filter(UserReviewTask.task_type == task_type)
    if assigned_to:
        q = q.filter(UserReviewTask.assigned_to == assigned_to)

    tasks = q.order_by(UserReviewTask.created_at.desc()).all()
    return [_task_to_dict(t) for t in tasks]


# ---------------------------------------------------------------------------
# Update review task
# ---------------------------------------------------------------------------


@router.put("/tasks/{task_id}")
def update_review_task(
    task_id: uuid.UUID,
    body: dict,
    db: Session = Depends(get_db),
) -> dict:
    """Update a review task's status and optionally notes/assigned_to.

    Allowed status transitions:
      pending → in_progress, approved, rejected, escalated
      in_progress → approved, rejected, escalated
    """
    task = db.query(UserReviewTask).filter(UserReviewTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="UserReviewTask not found")

    new_status = body.get("status")
    valid_statuses = {"pending", "in_progress", "approved", "rejected", "escalated"}
    if new_status and new_status not in valid_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of {sorted(valid_statuses)}",
        )

    if new_status:
        task.status = new_status

        # Mirror approval/rejection onto the candidate_clip itself
        if new_status in ("approved", "rejected") and task.candidate_clip_id:
            clip = (
                db.query(CandidateClip)
                .filter(CandidateClip.id == task.candidate_clip_id)
                .first()
            )
            if clip and clip.status == "candidate":
                clip.status = new_status
                logger.info(
                    "candidate_clip_status_updated",
                    clip_id=str(clip.id),
                    new_status=new_status,
                )

    if "notes" in body:
        task.notes = body["notes"]
    if "assigned_to" in body:
        task.assigned_to = body["assigned_to"]

    db.commit()
    db.refresh(task)

    logger.info(
        "review_task_updated",
        task_id=str(task_id),
        new_status=task.status,
    )
    return _task_to_dict(task)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task_to_dict(task: UserReviewTask) -> dict:
    return {
        "id": str(task.id),
        "task_type": task.task_type,
        "candidate_clip_id": str(task.candidate_clip_id) if task.candidate_clip_id else None,
        "assigned_to": task.assigned_to,
        "status": task.status,
        "notes": task.notes,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }
