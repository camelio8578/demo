"""
Celery task: generate_subtitles_and_copy

Generates SRT/ASS subtitle files, burns them into the rendered video,
then produces copy variants for each target platform.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import structlog
from celery import Celery

from app.config import settings
from app.db.base import SessionLocal
from app.db.models import (
    CandidateClip,
    CopyVariant,
    RenderedAsset,
    SubtitleAsset,
    TranscriptSegment,
)
from workers.copy.copy_generator import CopyGenerator
from workers.subtitle.subtitle_generator import SubtitleGenerator

log = structlog.get_logger(__name__)

celery_app = Celery("clipos", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

_TARGET_PLATFORMS = ["tiktok", "instagram", "youtube"]


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_subtitles_and_copy(self, rendered_asset_id: str) -> dict:
    """
    Main Celery task: generate subtitles and platform copy for a rendered clip.

    Steps:
    1. Load rendered_asset, candidate_clip, transcript_segments.
    2. Generate SRT and ASS subtitle files.
    3. Burn subtitles into video (creates captioned output).
    4. Create SubtitleAsset DB record with burn_in_complete=True.
    5. Generate copy for each platform.
    6. Create CopyVariant records.
    7. Update candidate_clip.status = rendered.
    """
    task_log = log.bind(
        task="generate_subtitles_and_copy",
        rendered_asset_id=rendered_asset_id,
    )
    task_log.info("task_started")

    db = SessionLocal()
    try:
        # Step 1: Load records
        asset = db.query(RenderedAsset).filter(
            RenderedAsset.id == uuid.UUID(rendered_asset_id)
        ).first()
        if not asset:
            raise ValueError(f"RenderedAsset {rendered_asset_id} not found")

        clip = db.query(CandidateClip).filter(
            CandidateClip.id == asset.candidate_clip_id
        ).first()
        if not clip:
            raise ValueError(
                f"CandidateClip {asset.candidate_clip_id} not found"
            )

        if not asset.output_path or not Path(asset.output_path).exists():
            raise ValueError(
                f"RenderedAsset {rendered_asset_id} has no valid output_path"
            )

        # Load transcript segments for this clip
        segments: list[TranscriptSegment] = []
        if clip.transcript_id:
            segments = (
                db.query(TranscriptSegment)
                .filter(TranscriptSegment.transcript_id == clip.transcript_id)
                .filter(TranscriptSegment.start_time >= clip.start_time)
                .filter(TranscriptSegment.end_time <= clip.end_time + 2.0)
                .order_by(TranscriptSegment.segment_index)
                .all()
            )

        task_log.info(
            "records_loaded",
            clip_id=str(clip.id),
            segment_count=len(segments),
            output_path=asset.output_path,
        )

        segment_dicts = [
            {
                "start_time": s.start_time,
                "end_time": s.end_time,
                "text": s.text,
            }
            for s in segments
        ]

        # Determine subtitle output directory
        clip_dir = Path(asset.output_path).parent
        srt_path = str(clip_dir / "subtitles.srt")
        ass_path = str(clip_dir / "subtitles.ass")
        captioned_path = str(clip_dir / "output_captioned.mp4")

        # Step 2: Generate SRT and ASS
        subtitle_gen = SubtitleGenerator()

        srt_out = subtitle_gen.generate_srt(
            segments=segment_dicts,
            output_path=srt_path,
            clip_start=clip.start_time,
        )
        task_log.info("srt_generated", path=srt_out)

        ass_out = subtitle_gen.generate_ass(
            segments=segment_dicts,
            output_path=ass_path,
            clip_start=clip.start_time,
            style_config=None,  # use DEFAULT_STYLE
        )
        task_log.info("ass_generated", path=ass_out)

        # Step 3: Burn subtitles
        burn_success = False
        try:
            subtitle_gen.burn_subtitles(
                video_path=asset.output_path,
                ass_path=ass_out,
                output_path=captioned_path,
            )
            burn_success = True
            task_log.info("subtitles_burned", captioned_path=captioned_path)
        except Exception as burn_exc:
            task_log.warning("subtitle_burn_failed", error=str(burn_exc))

        # Step 4: Create SubtitleAsset record
        subtitle_asset = SubtitleAsset(
            id=uuid.uuid4(),
            rendered_asset_id=asset.id,
            srt_path=srt_out,
            ass_path=ass_out,
            style_config=SubtitleGenerator.DEFAULT_STYLE,
            burn_in_complete=burn_success,
        )
        db.add(subtitle_asset)
        db.commit()
        task_log.info("subtitle_asset_created", id=str(subtitle_asset.id))

        # Step 5 & 6: Generate copy for each platform and persist CopyVariant
        copy_gen = CopyGenerator()
        llm_provider = getattr(settings, "LLM_PROVIDER", "none")
        created_variants: list[str] = []

        segment_text = clip.segment_text or " ".join(
            s.get("text", "") for s in segment_dicts
        )

        for platform in _TARGET_PLATFORMS:
            try:
                copy_data = copy_gen.generate_copy(
                    segment_text=segment_text,
                    platform=platform,
                    creator_name="",
                    llm_provider=llm_provider,
                )

                variant = CopyVariant(
                    id=uuid.uuid4(),
                    candidate_clip_id=clip.id,
                    platform=platform,
                    variant_index=0,
                    hook=copy_data.get("hook"),
                    title=copy_data.get("title"),
                    caption=copy_data.get("caption"),
                    hashtags=copy_data.get("hashtags", []),
                    llm_model_used=copy_data.get("llm_model_used"),
                    prompt_version=copy_data.get("prompt_version"),
                )
                db.add(variant)
                created_variants.append(platform)
                task_log.info("copy_variant_created", platform=platform)
            except Exception as copy_exc:
                task_log.warning(
                    "copy_generation_failed", platform=platform, error=str(copy_exc)
                )

        # Step 7: Update candidate_clip.status = rendered
        clip.status = "rendered"
        db.commit()
        task_log.info("candidate_clip_status_updated", status="rendered")

        return {
            "rendered_asset_id": rendered_asset_id,
            "subtitle_asset_id": str(subtitle_asset.id),
            "srt_path": srt_out,
            "ass_path": ass_out,
            "burn_in_complete": burn_success,
            "copy_variants_created": created_variants,
        }

    except Exception as exc:
        task_log.error("subtitle_copy_task_failed", error=str(exc))
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            task_log.error("max_retries_exceeded")
            raise
    finally:
        db.close()
