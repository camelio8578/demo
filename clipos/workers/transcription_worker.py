"""
Celery task: transcribe_video

Extracts audio from a downloaded source video and runs Whisper transcription.
Creates TranscriptSegment rows for each segment, then chains to scoring.
"""
from __future__ import annotations

import subprocess
import time
import uuid
from pathlib import Path

import structlog
from celery import Celery

from app.config import settings
from app.db.base import SessionLocal
from app.db.models import SourceVideo, Transcript, TranscriptSegment

log = structlog.get_logger(__name__)

celery_app = Celery("clipos", broker=settings.REDIS_URL, backend=settings.REDIS_URL)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_audio_path(video_id: str) -> Path:
    audio_dir = Path(settings.DATA_DIR) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    return audio_dir / f"{video_id}.wav"


def _extract_audio(video_path: str, audio_path: Path) -> None:
    """Extract mono 16 kHz WAV from video using ffmpeg."""
    log.info("extracting_audio", video_path=video_path, audio_path=str(audio_path))
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path),
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        log.error("audio_extraction_failed", stderr=exc.stderr)
        raise RuntimeError(f"ffmpeg audio extraction failed: {exc.stderr}") from exc


def _run_faster_whisper(audio_path: Path, model_name: str) -> list[dict]:
    """Transcribe using faster-whisper; returns list of segment dicts."""
    from faster_whisper import WhisperModel  # type: ignore

    log.info("transcribing_faster_whisper", model=model_name, audio=str(audio_path))
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(audio_path), beam_size=5)
    result = []
    for seg in segments:
        result.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
            "avg_logprob": seg.avg_logprob,
        })
    log.info("transcription_done_faster_whisper", segment_count=len(result))
    return result


def _run_openai_whisper(audio_path: Path, model_name: str) -> list[dict]:
    """Transcribe using openai-whisper; returns list of segment dicts."""
    import whisper  # type: ignore

    log.info("transcribing_openai_whisper", model=model_name, audio=str(audio_path))
    model = whisper.load_model(model_name)
    result = model.transcribe(str(audio_path))
    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip(),
            "avg_logprob": seg.get("avg_logprob", 0.0),
        })
    log.info("transcription_done_openai_whisper", segment_count=len(segments))
    return segments


def _transcribe(audio_path: Path, model_name: str) -> tuple[str, list[dict]]:
    """
    Run transcription with faster-whisper preferred, openai-whisper fallback.
    Returns (model_used, segments).
    """
    try:
        segments = _run_faster_whisper(audio_path, model_name)
        return "faster-whisper", segments
    except ImportError:
        log.warning("faster_whisper_not_available", fallback="openai-whisper")

    segments = _run_openai_whisper(audio_path, model_name)
    return "openai-whisper", segments


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def transcribe_video(self, source_video_id: str) -> dict:
    """
    Main Celery task: transcribe a downloaded source video.

    Steps:
    1. Load source_video from DB, get local_path and duration.
    2. Create transcript record with status=processing.
    3. Extract audio if needed.
    4. Run Whisper transcription.
    5. Persist TranscriptSegment rows.
    6. Update transcript: status=completed.
    7. Chain to scoring worker.
    """
    task_log = log.bind(task="transcribe_video", source_video_id=source_video_id)
    task_log.info("task_started")

    db = SessionLocal()
    transcript_id: str | None = None

    try:
        # Step 1: Load source video
        source_video = db.query(SourceVideo).filter(
            SourceVideo.id == uuid.UUID(source_video_id)
        ).first()
        if not source_video:
            raise ValueError(f"SourceVideo {source_video_id} not found")

        if not source_video.local_path:
            raise ValueError(f"SourceVideo {source_video_id} has no local_path")

        task_log.info("source_video_loaded", local_path=source_video.local_path)

        # Step 2: Create transcript record (status=processing)
        transcript = Transcript(
            id=uuid.uuid4(),
            source_video_id=source_video.id,
            status="processing",
            language="en",
        )
        db.add(transcript)
        db.commit()
        db.refresh(transcript)
        transcript_id = str(transcript.id)
        task_log = task_log.bind(transcript_id=transcript_id)
        task_log.info("transcript_record_created")

        # Step 3: Extract audio if needed
        audio_path = _get_audio_path(source_video_id)
        if not audio_path.exists():
            task_log.info("audio_not_found_extracting")
            _extract_audio(source_video.local_path, audio_path)
        else:
            task_log.info("audio_already_exists", audio_path=str(audio_path))

        # Step 4: Run transcription
        t_start = time.monotonic()
        model_name = settings.WHISPER_MODEL
        model_used, raw_segments = _transcribe(audio_path, model_name)
        processing_time_ms = int((time.monotonic() - t_start) * 1000)

        task_log.info(
            "transcription_complete",
            model_used=model_used,
            segment_count=len(raw_segments),
            processing_time_ms=processing_time_ms,
        )

        # Step 5: Persist segments
        full_text_parts: list[str] = []
        for idx, seg in enumerate(raw_segments):
            text = seg.get("text", "").strip()
            if not text:
                continue
            full_text_parts.append(text)
            # confidence from avg_logprob (logprob is negative; map to [0,1])
            avg_logprob = seg.get("avg_logprob", -1.0)
            confidence = max(0.0, min(1.0, 1.0 + avg_logprob / 5.0))

            segment_row = TranscriptSegment(
                id=uuid.uuid4(),
                transcript_id=transcript.id,
                segment_index=idx,
                start_time=float(seg.get("start", 0.0)),
                end_time=float(seg.get("end", 0.0)),
                text=text,
                confidence=round(confidence, 4),
            )
            db.add(segment_row)

        full_text = " ".join(full_text_parts)
        word_count = len(full_text.split())

        # Step 6: Update transcript to completed
        transcript.status = "completed"
        transcript.model_used = model_used
        transcript.full_text = full_text
        transcript.word_count = word_count
        transcript.processing_time_ms = processing_time_ms
        db.commit()

        task_log.info(
            "transcript_completed",
            word_count=word_count,
            processing_time_ms=processing_time_ms,
        )

        # Step 7: Chain to scoring worker
        try:
            from workers.scoring_worker import score_video_candidates
            score_video_candidates.delay(source_video_id)
            task_log.info("scoring_task_triggered")
        except Exception as chain_exc:
            task_log.warning("scoring_chain_failed", error=str(chain_exc))

        return {
            "source_video_id": source_video_id,
            "transcript_id": transcript_id,
            "word_count": word_count,
            "segment_count": len(raw_segments),
            "processing_time_ms": processing_time_ms,
            "model_used": model_used,
        }

    except Exception as exc:
        task_log.error("transcription_failed", error=str(exc))
        if transcript_id:
            try:
                transcript = db.query(Transcript).filter(
                    Transcript.id == uuid.UUID(transcript_id)
                ).first()
                if transcript:
                    transcript.status = "failed"
                    transcript.failure_reason = str(exc)
                    db.commit()
            except Exception as db_exc:
                task_log.error("failed_to_update_transcript_status", error=str(db_exc))

        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            task_log.error("max_retries_exceeded")
            raise
    finally:
        db.close()
