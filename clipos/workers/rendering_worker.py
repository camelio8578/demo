"""
Celery task: render_clip

Renders a CandidateClip to a 9:16 MP4 using ClipRenderer and persists
a RenderedAsset record. Chains to subtitle/copy generation on success.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import structlog
from celery import Celery

from app.config import settings
from app.db.base import SessionLocal
from app.db.models import CandidateClip, RenderedAsset, SourceVideo
from workers.rendering.renderer import ClipRenderer

log = structlog.get_logger(__name__)

celery_app = Celery("clipos", broker=settings.REDIS_URL, backend=settings.REDIS_URL)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def render_clip(self, candidate_clip_id: str) -> dict:
    """
    Main Celery task: render a candidate clip to a 9:16 MP4.

    Steps:
    1. Load candidate_clip from DB.
    2. Load source_video to get local_path.
    3. Create rendered_asset record with status=rendering.
    4. Call ClipRenderer.render_clip().
    5. Update rendered_asset: status=completed with all metadata.
    6. Chain to subtitle/copy generation.
    """
    task_log = log.bind(task="render_clip", candidate_clip_id=candidate_clip_id)
    task_log.info("task_started")

    db = SessionLocal()
    asset_id: str | None = None

    try:
        # Step 1: Load candidate clip
        clip = db.query(CandidateClip).filter(
            CandidateClip.id == uuid.UUID(candidate_clip_id)
        ).first()
        if not clip:
            raise ValueError(f"CandidateClip {candidate_clip_id} not found")

        # Step 2: Load source video
        source_video = db.query(SourceVideo).filter(
            SourceVideo.id == clip.source_video_id
        ).first()
        if not source_video:
            raise ValueError(f"SourceVideo {clip.source_video_id} not found")
        if not source_video.local_path:
            raise ValueError(
                f"SourceVideo {source_video.id} has no local_path — not downloaded yet"
            )

        task_log.info(
            "clip_loaded",
            start_time=clip.start_time,
            end_time=clip.end_time,
            source_path=source_video.local_path,
        )

        # Step 3: Create rendered_asset (status=rendering)
        asset = RenderedAsset(
            id=uuid.uuid4(),
            candidate_clip_id=clip.id,
            status="rendering",
            render_job_id=self.request.id,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        asset_id = str(asset.id)
        task_log = task_log.bind(asset_id=asset_id)
        task_log.info("rendered_asset_record_created")

        # Step 4: Determine output path
        clip_dir = Path(settings.DATA_DIR) / "clips" / candidate_clip_id
        clip_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(clip_dir / "output.mp4")

        # Step 5: Render
        renderer = ClipRenderer()
        render_result = renderer.render_clip(
            source_video_path=source_video.local_path,
            start_time=clip.start_time,
            end_time=clip.end_time,
            output_path=output_path,
        )

        task_log.info("render_complete", render_result=render_result)

        # Step 6: Update rendered_asset
        asset.status = "completed"
        asset.output_path = render_result["output_path"]
        asset.thumbnail_path = render_result.get("thumbnail_path")
        asset.file_size_bytes = render_result.get("file_size")
        asset.resolution = render_result.get("resolution")
        asset.fps = render_result.get("fps")
        asset.duration_seconds = render_result.get("duration")
        db.commit()

        task_log.info("rendered_asset_updated", status="completed")

        # Step 7: Chain to subtitle/copy generation
        try:
            from workers.subtitle_copy_worker import generate_subtitles_and_copy
            generate_subtitles_and_copy.delay(asset_id)
            task_log.info("subtitle_copy_task_triggered", asset_id=asset_id)
        except Exception as chain_exc:
            task_log.warning("subtitle_copy_chain_failed", error=str(chain_exc))

        return {
            "candidate_clip_id": candidate_clip_id,
            "asset_id": asset_id,
            "output_path": render_result["output_path"],
            "file_size": render_result.get("file_size"),
            "resolution": render_result.get("resolution"),
        }

    except Exception as exc:
        task_log.error("render_failed", error=str(exc))
        if asset_id:
            try:
                asset = db.query(RenderedAsset).filter(
                    RenderedAsset.id == uuid.UUID(asset_id)
                ).first()
                if asset:
                    asset.status = "failed"
                    asset.failure_reason = str(exc)
                    db.commit()
            except Exception as db_exc:
                task_log.error("failed_to_update_asset_status", error=str(db_exc))

        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            task_log.error("max_retries_exceeded")
            raise
    finally:
        db.close()
