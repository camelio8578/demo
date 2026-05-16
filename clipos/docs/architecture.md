# ClipOS Architecture

## Overview

ClipOS is an autonomous short-form video clipping system. It monitors creator
channels, ingests videos, transcribes them, scores candidate clips, renders
short-form output, generates platform-specific copy, and publishes — all
orchestrated via Celery task queues.

## Data Flow

```
Creator Channel (YouTube / TikTok / etc.)
        │
        ▼
MonitoredSource polling (Celery beat — future)
        │  source_url
        ▼
ingest_video_task (queue: ingestion)
        │  1. yt-dlp metadata fetch
        │  2. yt-dlp download → DATA_DIR/videos/{id}.mp4
        │  3. ffmpeg audio extract → DATA_DIR/audio/{id}.wav
        │  4. Create source_video record
        ▼
transcribe_video_task (queue: transcription)
        │  Whisper / OpenAI Whisper API
        │  Creates transcript + transcript_segments
        ▼
scoring_worker (queue: scoring)           [Phase 5+]
        │  Scores candidate clips
        │  Creates candidate_clips + clip_scores
        ▼
rendering_worker (queue: rendering)       [Phase 6+]
        │  FFmpeg clip render
        │  Subtitle burn-in
        │  Creates rendered_assets + subtitle_assets
        ▼
copy_worker (queue: scoring)              [Phase 7+]
        │  LLM copy generation per platform
        │  Creates copy_variants
        ▼
publishing_worker (queue: publishing)     [Phase 8+]
        │  Platform API upload
        │  Creates publishing_jobs + publish_attempts
        ▼
analytics_worker (queue: scoring)         [Phase 9+]
        │  Periodic analytics snapshots
        │  Creates analytics_snapshots
```

## Service Map

| Service | Port | Purpose |
|---------|------|---------|
| api | 8000 | FastAPI REST API |
| postgres | 5432 | Primary database |
| redis | 6379 | Celery broker + backend |
| worker_ingestion | — | Download + audio extract |
| worker_transcription | — | Speech-to-text |
| worker_rendering | — | FFmpeg clip rendering |
| worker_publishing | — | Platform API publishing |
| flower | 5555 | Celery task monitor |
| admin | 3000 | Next.js operator dashboard |

## Queue Architecture

Each worker type runs on a dedicated queue to allow independent scaling:

- `ingestion` — I/O bound, disk-heavy (yt-dlp, ffmpeg)
- `transcription` — CPU/GPU bound (Whisper)
- `scoring` — CPU bound (ML scoring)
- `rendering` — CPU/GPU bound (FFmpeg)
- `publishing` — Network bound (platform APIs)

## Database

PostgreSQL with SQLAlchemy 2.0 + Alembic migrations.
All PKs are UUID v4. `created_at` defaults to `func.now()` server-side.

See `apps/api/app/db/models.py` for the complete schema (20 tables).
