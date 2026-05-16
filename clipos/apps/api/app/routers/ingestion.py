"""Ingestion API endpoints."""

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models import Creator, SourceVideo, Transcript
from app.dependencies import get_db
from app.schemas.ingestion import (
    IngestRequest,
    IngestResponse,
    RetranscribeResponse,
    SourceVideoListResponse,
    SourceVideoResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["ingestion"])


@router.post("/ingest", response_model=IngestResponse, status_code=202)
def ingest_video(body: IngestRequest, db: Session = Depends(get_db)) -> IngestResponse:
    creator = db.query(Creator).filter(Creator.id == body.creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    # Check for existing video with same URL unless force_redownload
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

    # Dispatch Celery task
    try:
        from workers.ingestion_worker import ingest_video_task

        result = ingest_video_task.delay(
            source_url=body.source_url,
            creator_id=str(body.creator_id),
            source_video_id=str(video.id),
        )
        job_id = result.id
    except Exception as exc:
        logger.warning("celery_dispatch_failed", error=str(exc))
        job_id = f"local-{video.id}"

    logger.info("ingest_queued", video_id=str(video.id), job_id=job_id)
    return IngestResponse(
        job_id=job_id,
        source_video_id=video.id,
        message="Ingestion job queued",
    )


@router.get("/videos", response_model=SourceVideoListResponse)
def list_videos(
    status: Optional[str] = Query(None),
    creator_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
) -> SourceVideoListResponse:
    q = db.query(SourceVideo)
    if status:
        q = q.filter(SourceVideo.status == status)
    if creator_id:
        q = q.filter(SourceVideo.creator_id == creator_id)
    items = q.all()
    return SourceVideoListResponse(items=items, total=len(items))


@router.get("/videos/{video_id}", response_model=SourceVideoResponse)
def get_video(video_id: uuid.UUID, db: Session = Depends(get_db)) -> SourceVideoResponse:
    video = db.query(SourceVideo).filter(SourceVideo.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.post("/videos/{video_id}/retranscribe", response_model=RetranscribeResponse)
def retranscribe_video(
    video_id: uuid.UUID, db: Session = Depends(get_db)
) -> RetranscribeResponse:
    video = db.query(SourceVideo).filter(SourceVideo.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not video.local_path:
        raise HTTPException(
            status_code=422,
            detail="Video has no local file; run ingestion first",
        )

    transcript = Transcript(
        id=uuid.uuid4(),
        source_video_id=video_id,
        status="pending",
    )
    db.add(transcript)
    db.commit()
    db.refresh(transcript)

    try:
        from workers.ingestion_worker import transcribe_video_task

        result = transcribe_video_task.delay(
            source_video_id=str(video_id),
            transcript_id=str(transcript.id),
            audio_path=video.local_path.replace(".mp4", ".wav"),
        )
        job_id = result.id
    except Exception as exc:
        logger.warning("celery_dispatch_failed", error=str(exc))
        job_id = f"local-{transcript.id}"

    logger.info("retranscribe_queued", video_id=str(video_id), job_id=job_id)
    return RetranscribeResponse(job_id=job_id, message="Transcription job queued")
