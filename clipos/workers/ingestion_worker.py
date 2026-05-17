"""Ingestion Celery worker: download video, extract audio, trigger transcription."""

import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog

from workers.celery_app import app as celery_app

logger = structlog.get_logger(__name__)

DATA_DIR = os.getenv("DATA_DIR", "/data")
VIDEO_DIR = Path(DATA_DIR) / "videos"
AUDIO_DIR = Path(DATA_DIR) / "audio"


def _get_db_session():
    """Create a standalone DB session for use inside Celery tasks."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../apps/api"))

    from app.db.base import SessionLocal
    return SessionLocal()


def _update_video_status(session, video_id: str, status: str, **kwargs) -> None:
    from app.db.models import SourceVideo

    video = session.query(SourceVideo).filter(SourceVideo.id == uuid.UUID(video_id)).first()
    if not video:
        logger.error("video_not_found_in_db", video_id=video_id)
        return
    video.status = status
    for key, value in kwargs.items():
        setattr(video, key, value)
    session.commit()


@celery_app.task(name="workers.ingestion_worker.ingest_video_task", bind=True, max_retries=3)
def ingest_video_task(
    self,
    source_url: str,
    creator_id: str,
    source_video_id: str,
    monitored_source_id: str | None = None,
):
    """
    Full ingestion pipeline:
    1. Fetch video metadata via yt-dlp
    2. Update source_video record with status=downloading
    3. Download video to DATA_DIR/videos/{video_id}.mp4
    4. Update source_video: status=downloaded, local_path, file_size_bytes, duration_seconds
    5. Extract audio to DATA_DIR/audio/{video_id}.wav (FFmpeg)
    6. Chain transcription task
    """
    log = logger.bind(
        task_id=self.request.id,
        source_video_id=source_video_id,
        source_url=source_url,
        creator_id=creator_id,
    )
    log.info("ingest_task_started")

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    video_path = VIDEO_DIR / f"{source_video_id}.mp4"
    audio_path = AUDIO_DIR / f"{source_video_id}.wav"

    session = _get_db_session()
    try:
        # Step 1: Fetch metadata
        log.info("fetching_metadata")
        _update_video_status(session, source_video_id, "downloading")

        meta_result = subprocess.run(
            [
                "yt-dlp",
                "--dump-json",
                "--no-playlist",
                source_url,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        title = None
        description = None
        duration_seconds = None
        platform_video_id = None
        published_at = None

        if meta_result.returncode == 0:
            import json
            meta = json.loads(meta_result.stdout)
            title = meta.get("title")
            description = meta.get("description")
            duration_seconds = meta.get("duration")
            platform_video_id = meta.get("id")
            upload_date = meta.get("upload_date")
            if upload_date:
                published_at = datetime.strptime(upload_date, "%Y%m%d").replace(
                    tzinfo=timezone.utc
                )
            log.info("metadata_fetched", title=title, duration_seconds=duration_seconds)
        else:
            log.warning(
                "metadata_fetch_failed",
                stderr=meta_result.stderr[:500],
            )

        # Update with metadata
        from app.db.models import SourceVideo
        video = session.query(SourceVideo).filter(
            SourceVideo.id == uuid.UUID(source_video_id)
        ).first()
        if video:
            video.title = title
            video.description = description
            video.duration_seconds = duration_seconds
            video.platform_video_id = platform_video_id
            video.published_at = published_at
            session.commit()

        # Step 2: Download video
        log.info("downloading_video", output_path=str(video_path))
        dl_result = subprocess.run(
            [
                "yt-dlp",
                "--no-playlist",
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "--merge-output-format", "mp4",
                "-o", str(video_path),
                source_url,
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )

        if dl_result.returncode != 0:
            raise RuntimeError(
                f"yt-dlp download failed: {dl_result.stderr[:500]}"
            )

        file_size = video_path.stat().st_size if video_path.exists() else None
        log.info("video_downloaded", file_size_bytes=file_size)

        _update_video_status(
            session,
            source_video_id,
            "downloaded",
            local_path=str(video_path),
            file_size_bytes=file_size,
            downloaded_at=datetime.now(timezone.utc),
        )

        # Step 3: Extract audio
        log.info("extracting_audio", audio_path=str(audio_path))
        audio_result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", str(video_path),
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if audio_result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg audio extraction failed: {audio_result.stderr[:500]}"
            )

        log.info("audio_extracted", audio_path=str(audio_path))

        # Step 4: Trigger transcription
        transcript_id = str(uuid.uuid4())
        from app.db.models import Transcript
        transcript = Transcript(
            id=uuid.UUID(transcript_id),
            source_video_id=uuid.UUID(source_video_id),
            status="pending",
        )
        session.add(transcript)
        session.commit()

        transcribe_video_task.apply_async(
            kwargs={
                "source_video_id": source_video_id,
                "transcript_id": transcript_id,
                "audio_path": str(audio_path),
            },
            queue="transcription",
        )
        log.info("transcription_task_queued", transcript_id=transcript_id)

    except Exception as exc:
        log.error("ingest_task_failed", error=str(exc))
        try:
            _update_video_status(
                session,
                source_video_id,
                "failed",
                failure_reason=str(exc),
            )
        except Exception as db_exc:
            log.error("failed_to_update_db_on_error", error=str(db_exc))
        raise self.retry(exc=exc, countdown=60)
    finally:
        session.close()

    log.info("ingest_task_completed", source_video_id=source_video_id)
    return {"source_video_id": source_video_id, "audio_path": str(audio_path)}


@celery_app.task(
    name="workers.ingestion_worker.transcribe_video_task",
    bind=True,
    max_retries=2,
)
def transcribe_video_task(
    self,
    source_video_id: str,
    transcript_id: str,
    audio_path: str,
):
    """
    Transcription task (stub — full implementation in transcription_worker).
    Updates transcript status and logs. Real transcription logic
    (Whisper / OpenAI / etc.) lives in workers/transcription_worker.py.
    """
    log = logger.bind(
        task_id=self.request.id,
        source_video_id=source_video_id,
        transcript_id=transcript_id,
        audio_path=audio_path,
    )
    log.info("transcription_task_started")

    session = _get_db_session()
    try:
        from app.db.models import Transcript

        transcript = session.query(Transcript).filter(
            Transcript.id == uuid.UUID(transcript_id)
        ).first()
        if not transcript:
            raise ValueError(f"Transcript {transcript_id} not found")

        transcript.status = "processing"
        session.commit()
        log.info("transcription_status_set_processing")

        # Stub: mark as completed with placeholder
        # Real implementation delegates to transcription_worker
        transcript.status = "completed"
        transcript.full_text = ""
        transcript.word_count = 0
        transcript.model_used = "stub"
        session.commit()
        log.info("transcription_stub_completed")

    except Exception as exc:
        log.error("transcription_task_failed", error=str(exc))
        try:
            from app.db.models import Transcript
            transcript = session.query(Transcript).filter(
                Transcript.id == uuid.UUID(transcript_id)
            ).first()
            if transcript:
                transcript.status = "failed"
                transcript.failure_reason = str(exc)
                session.commit()
        except Exception as db_exc:
            log.error("failed_to_update_transcript_on_error", error=str(db_exc))
        raise self.retry(exc=exc, countdown=30)
    finally:
        session.close()

    log.info("transcription_task_completed", transcript_id=transcript_id)
    return {"transcript_id": transcript_id}
