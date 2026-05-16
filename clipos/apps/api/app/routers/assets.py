"""
Rendered asset endpoints.

POST /api/v1/candidates/{id}/render     — trigger render job
GET  /api/v1/assets/{id}               — get rendered asset details
GET  /api/v1/assets/{id}/download      — redirect to file or stream
POST /api/v1/assets/{id}/rerender      — re-queue render
"""
from __future__ import annotations

import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.models import CandidateClip, RenderedAsset
from app.dependencies import get_db
from app.schemas.assets import RenderedAssetOut, RenderRequest, ReRenderRequest

log = structlog.get_logger(__name__)

router = APIRouter(tags=["assets"])


@router.post(
    "/api/v1/candidates/{candidate_id}/render",
    response_model=RenderedAssetOut,
    status_code=202,
)
def trigger_render(
    candidate_id: uuid.UUID,
    body: RenderRequest = RenderRequest(),
    db: Session = Depends(get_db),
) -> RenderedAsset:
    """
    Trigger an async render job for a candidate clip.
    Creates a RenderedAsset in status=pending and queues the Celery task.
    """
    clip = db.query(CandidateClip).filter(CandidateClip.id == candidate_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Candidate clip not found")

    # Create asset record in pending state
    asset = RenderedAsset(
        id=uuid.uuid4(),
        candidate_clip_id=clip.id,
        status="pending",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    job_id: str = str(asset.id)
    try:
        from workers.rendering_worker import render_clip

        task = render_clip.delay(str(candidate_id))
        job_id = task.id
        asset.render_job_id = job_id
        db.commit()
    except Exception as exc:
        log.warning("render_trigger_failed", error=str(exc))

    log.info(
        "render_triggered",
        candidate_id=str(candidate_id),
        asset_id=str(asset.id),
        job_id=job_id,
    )
    return asset


@router.get("/api/v1/assets/{asset_id}", response_model=RenderedAssetOut)
def get_asset(asset_id: uuid.UUID, db: Session = Depends(get_db)) -> RenderedAsset:
    """Get details for a rendered asset."""
    asset = db.query(RenderedAsset).filter(RenderedAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Rendered asset not found")
    return asset


@router.get("/api/v1/assets/{asset_id}/download")
def download_asset(
    asset_id: uuid.UUID, db: Session = Depends(get_db)
) -> FileResponse:
    """
    Stream or redirect to the rendered video file.
    Returns 404 if the asset is not yet completed or the file is missing.
    """
    asset = db.query(RenderedAsset).filter(RenderedAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Rendered asset not found")

    if asset.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Asset is not ready (status={asset.status})",
        )

    if not asset.output_path or not Path(asset.output_path).exists():
        raise HTTPException(
            status_code=404, detail="Video file not found on disk"
        )

    log.info("asset_download", asset_id=str(asset_id), path=asset.output_path)
    return FileResponse(
        path=asset.output_path,
        media_type="video/mp4",
        filename=f"clip_{asset_id}.mp4",
    )


@router.post(
    "/api/v1/assets/{asset_id}/rerender",
    response_model=RenderedAssetOut,
    status_code=202,
)
def rerender_asset(
    asset_id: uuid.UUID,
    body: ReRenderRequest = ReRenderRequest(),
    db: Session = Depends(get_db),
) -> RenderedAsset:
    """Re-queue the render job for an existing rendered asset."""
    asset = db.query(RenderedAsset).filter(RenderedAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Rendered asset not found")

    if asset.status == "rendering" and not body.force:
        raise HTTPException(
            status_code=409,
            detail="Asset is already rendering. Pass force=true to override.",
        )

    # Reset asset to pending
    asset.status = "pending"
    asset.failure_reason = None
    asset.output_path = None
    asset.thumbnail_path = None
    db.commit()

    candidate_clip_id = str(asset.candidate_clip_id)
    job_id: str = asset_id.hex

    try:
        from workers.rendering_worker import render_clip

        task = render_clip.delay(candidate_clip_id)
        job_id = task.id
        asset.render_job_id = job_id
        db.commit()
    except Exception as exc:
        log.warning("rerender_trigger_failed", error=str(exc))

    db.refresh(asset)
    log.info(
        "rerender_triggered",
        asset_id=str(asset_id),
        candidate_clip_id=candidate_clip_id,
        job_id=job_id,
    )
    return asset
