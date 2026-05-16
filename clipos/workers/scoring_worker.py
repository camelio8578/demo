"""
Celery task: score_video_candidates

Uses a sliding window over transcript segments to generate candidate clips,
scores each with ClipScorer, persists results, and optionally auto-renders
the top candidates.
"""
from __future__ import annotations

import uuid
from typing import Any

import structlog
from celery import Celery

from app.config import settings
from app.db.base import SessionLocal
from app.db.models import (
    CandidateClip,
    ClipScore,
    SourceVideo,
    Transcript,
    TranscriptSegment,
)
from workers.scoring.scorer import ClipScorer

log = structlog.get_logger(__name__)

celery_app = Celery("clipos", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

# Sliding-window parameters
_WINDOW_MIN_SEC: float = 30.0
_WINDOW_MAX_SEC: float = 120.0
_WINDOW_STEP_SEC: float = 15.0
_TOP_N_KEEP: int = 10
_AUTO_RENDER_TOP_N: int = 5


def _build_windows(
    segments: list[TranscriptSegment],
    video_duration: float | None,
) -> list[dict[str, Any]]:
    """
    Generate all candidate windows via a sliding window over transcript segments.

    Returns list of dicts with keys: start_time, end_time, text, segment_texts.
    """
    if not segments:
        return []

    sorted_segs = sorted(segments, key=lambda s: s.start_time)
    max_time = video_duration or (sorted_segs[-1].end_time if sorted_segs else 0.0)

    windows: list[dict[str, Any]] = []
    start = sorted_segs[0].start_time

    while start < max_time:
        for window_size in [30, 45, 60, 75, 90, 105, 120]:
            end = start + window_size
            if end > max_time + 5:  # allow slight overshoot
                continue

            # Collect segments within this window
            window_segs = [
                s for s in sorted_segs
                if s.start_time >= start and s.end_time <= end
            ]
            if not window_segs:
                continue

            duration = end - start
            if duration < _WINDOW_MIN_SEC or duration > _WINDOW_MAX_SEC:
                continue

            text = " ".join(s.text for s in window_segs if s.text)
            if not text.strip():
                continue

            windows.append({
                "start_time": start,
                "end_time": end,
                "duration": duration,
                "text": text,
                "segment_count": len(window_segs),
            })

        start += _WINDOW_STEP_SEC

    return windows


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def score_video_candidates(self, source_video_id: str) -> dict:
    """
    Main Celery task: generate and score candidate clips for a source video.

    Steps:
    1. Load transcript and all transcript_segments.
    2. Generate candidate windows (30-120s, step 15s).
    3. For each window: create CandidateClip + ClipScore.
    4. Keep top N by total_score.
    5. Optionally trigger rendering for top 5.
    """
    task_log = log.bind(task="score_video_candidates", source_video_id=source_video_id)
    task_log.info("task_started")

    db = SessionLocal()
    try:
        # Step 1: Load source video, transcript, and segments
        source_video = db.query(SourceVideo).filter(
            SourceVideo.id == uuid.UUID(source_video_id)
        ).first()
        if not source_video:
            raise ValueError(f"SourceVideo {source_video_id} not found")

        transcript = (
            db.query(Transcript)
            .filter(
                Transcript.source_video_id == source_video.id,
                Transcript.status == "completed",
            )
            .order_by(Transcript.created_at.desc())
            .first()
        )
        if not transcript:
            raise ValueError(
                f"No completed transcript found for source_video {source_video_id}"
            )

        segments = (
            db.query(TranscriptSegment)
            .filter(TranscriptSegment.transcript_id == transcript.id)
            .order_by(TranscriptSegment.segment_index)
            .all()
        )

        task_log.info(
            "transcript_loaded",
            transcript_id=str(transcript.id),
            segment_count=len(segments),
        )

        all_segment_dicts = [
            {
                "text": s.text,
                "start_time": s.start_time,
                "end_time": s.end_time,
            }
            for s in segments
        ]

        # Step 2: Build candidate windows
        windows = _build_windows(segments, source_video.duration_seconds)
        task_log.info("candidate_windows_built", window_count=len(windows))

        scorer = ClipScorer()
        scored_candidates: list[tuple[float, CandidateClip, ClipScore]] = []

        # Step 3: Score each window
        for win in windows:
            # Create candidate_clip record
            clip = CandidateClip(
                id=uuid.uuid4(),
                source_video_id=source_video.id,
                transcript_id=transcript.id,
                start_time=win["start_time"],
                end_time=win["end_time"],
                duration_seconds=win["duration"],
                segment_text=win["text"],
                status="candidate",
            )
            db.add(clip)
            db.flush()  # get clip.id without full commit

            # Score the candidate
            score_result = scorer.score_candidate(
                segment_text=win["text"],
                start_time=win["start_time"],
                end_time=win["end_time"],
                all_segments=all_segment_dicts,
                audio_path=None,
                weights=None,
                creator_clips_performance=[],
            )

            clip_score = ClipScore(
                id=uuid.uuid4(),
                candidate_clip_id=clip.id,
                total_score=score_result["total_score"],
                speech_density=score_result["speech_density"],
                sentiment_score=score_result["sentiment_score"],
                hook_phrase_score=score_result["hook_phrase_score"],
                pause_burst_score=score_result["pause_burst_score"],
                novelty_score=score_result["novelty_score"],
                completeness_score=score_result["completeness_score"],
                duration_fit_score=score_result["duration_fit_score"],
                risk_flag_score=score_result["risk_flag_score"],
                prior_performance_score=score_result["prior_performance_score"],
                scoring_version=settings.SCORING_VERSION,
            )
            db.add(clip_score)
            scored_candidates.append((score_result["total_score"], clip, clip_score))

        db.commit()
        task_log.info("candidates_scored", total=len(scored_candidates))

        # Step 4: Keep top N
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_n = scored_candidates[:_TOP_N_KEEP]
        bottom = scored_candidates[_TOP_N_KEEP:]

        # Soft-reject candidates outside top N (status stays "candidate" for now,
        # they just won't be auto-rendered)
        task_log.info(
            "top_candidates_selected",
            top_count=len(top_n),
            dropped_count=len(bottom),
            top_scores=[round(s, 4) for s, _, __ in top_n],
        )

        # Step 5: Auto-render top candidates if enabled
        auto_render = getattr(settings, "AUTO_RENDER", False)
        if auto_render:
            from workers.rendering_worker import render_clip

            render_top = top_n[:_AUTO_RENDER_TOP_N]
            for _, clip, _ in render_top:
                try:
                    render_clip.delay(str(clip.id))
                    task_log.info("render_task_triggered", clip_id=str(clip.id))
                except Exception as render_exc:
                    task_log.warning(
                        "render_trigger_failed",
                        clip_id=str(clip.id),
                        error=str(render_exc),
                    )
        else:
            task_log.info("auto_render_disabled")

        return {
            "source_video_id": source_video_id,
            "transcript_id": str(transcript.id),
            "windows_evaluated": len(windows),
            "candidates_created": len(scored_candidates),
            "top_n_kept": len(top_n),
            "top_score": top_n[0][0] if top_n else 0.0,
        }

    except Exception as exc:
        task_log.error("scoring_failed", error=str(exc))
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            task_log.error("max_retries_exceeded")
            raise
    finally:
        db.close()
