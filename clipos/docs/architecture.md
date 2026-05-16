# ClipOS Architecture

## System Diagram

```
Creator Channel (YouTube / TikTok / Instagram / etc.)
        │
        ▼
MonitoredSource polling (Celery beat — scheduled)
        │  source_url
        ▼
┌─────────────────────────────────────────────────────┐
│                   FastAPI (port 8000)                │
│  POST /api/v1/ingest                                 │
└───────────────────────┬─────────────────────────────┘
                        │  Celery task dispatch
                        ▼
              Redis (broker + backend)
                        │
        ┌───────────────┼────────────────────┐
        ▼               ▼                    ▼
  queue:ingestion  queue:transcription  queue:scoring
        │               │                    │
        ▼               ▼                    ▼
  ingest_video_  transcribe_video_   score_candidates_
     task            task               task
        │               │                    │
        │  ┌────────────┘                    │
        ▼  ▼                                 ▼
   PostgreSQL (source_videos,          candidate_clips +
   transcripts, segments)              clip_scores
                                             │
                                 ┌───────────┴──────────┐
                                 ▼                       ▼
                          queue:rendering         queue:scoring
                                 │                       │
                          render_clip_task    generate_copy_task
                                 │                       │
                                 ▼                       ▼
                          rendered_assets          copy_variants
                                 │
                                 ▼
                          queue:publishing
                                 │
                          publish_clip_task
                                 │
                                 ▼
                    Platform API (YouTube/TikTok/Instagram)
                                 │
                                 ▼
                         publishing_jobs +
                         publish_attempts +
                         analytics_snapshots
```

## Module Descriptions

### apps/api/

The FastAPI backend. All HTTP endpoints, dependency injection, database sessions,
and Pydantic schemas live here.

| Module | Purpose |
|--------|---------|
| app/main.py | FastAPI app factory, router registration, lifespan |
| app/db/models.py | SQLAlchemy 2.0 models (20 tables, all UUID PKs) |
| app/db/session.py | Engine creation, get_db dependency |
| app/api/v1/routers/ | One router per resource group |
| app/schemas/ | Pydantic v2 request/response schemas |
| app/core/config.py | Settings (reads from env via pydantic-settings) |

### workers/

Celery task definitions. Each queue has a dedicated worker process in Docker
Compose, allowing independent scaling.

| Module | Queue | Purpose |
|--------|-------|---------|
| workers/ingestion.py | ingestion | yt-dlp download + ffmpeg audio extract |
| workers/transcription.py | transcription | Whisper speech-to-text + segment storage |
| workers/scoring.py | scoring | 9-signal candidate scoring + LLM rescore |
| workers/rendering.py | rendering | FFmpeg clip extraction + subtitle burn-in |
| workers/publishing.py | publishing | Platform API upload + retry logic |
| workers/celery_app.py | — | Celery app factory, broker/backend config |

### libs/

Shared Python utilities used by both the API and workers.

| Module | Purpose |
|--------|---------|
| libs/storage.py | Local filesystem or S3/MinIO abstraction |
| libs/ffmpeg.py | FFmpeg wrapper (clip extract, audio, subtitles) |
| libs/whisper_client.py | Local Whisper or OpenAI Whisper API |

### apps/admin/

Next.js 14 operator dashboard. Server-side rendered, communicates with the
FastAPI backend via NEXT_PUBLIC_API_URL.

### infra/

Docker Compose definition and environment configuration.

## Data Flow Narrative

1. **Ingestion**: Operator calls `POST /api/v1/ingest` with a source URL and
   creator ID. The API creates a `source_video` record with status `pending`
   and enqueues `ingest_video_task` on the `ingestion` queue.

2. **Download**: `ingest_video_task` uses yt-dlp to fetch video metadata and
   download the video to `DATA_DIR/videos/{id}.mp4`. FFmpeg extracts audio to
   `DATA_DIR/audio/{id}.wav`. On completion, chains to `transcribe_video_task`.

3. **Transcription**: `transcribe_video_task` runs Whisper (local CPU or
   OpenAI API) on the extracted audio. Word-level timestamps are stored as
   `transcript_segments` rows. Chains to `score_candidates_task`.

4. **Scoring**: `score_candidates_task` applies 9 heuristic signals to identify
   candidate clips. Signals include speech density, sentiment, hook phrases,
   pause/burst patterns, and duration fit. Top candidates are stored as
   `candidate_clips` with `clip_scores`. Auto-renders top N if
   `AUTO_RENDER_ENABLED=true`.

5. **Rendering**: `render_clip_task` uses FFmpeg to extract the candidate
   time window, optionally reframe to 9:16 (center crop), burn in ASS/SRT
   subtitles, and write the output to `DATA_DIR/rendered/{id}.mp4`. Creates
   a `rendered_asset` record.

6. **Copy Generation**: `generate_copy_task` calls the configured LLM provider
   (or rule-based fallback) to produce platform-specific hook, title, caption,
   and hashtags. Stores multiple variants in `copy_variants`.

7. **Human Review Gate**: Operator reviews candidates and rendered clips in the
   admin dashboard. Sets `candidate_clips.status = approved` to release to
   publishing.

8. **Publishing**: `publish_clip_task` calls the appropriate `PublishingAdapter`
   subclass (YouTube, TikTok, Instagram). On success, stores the platform post
   ID in `publishing_jobs`. Retries with exponential backoff on failure.

9. **Analytics**: Scheduled tasks poll platform APIs for view/engagement metrics
   and store snapshots in `analytics_snapshots`. Future: feedback loop to
   scoring weights.

## Queue Routing

| Queue | Worker Concurrency | Bottleneck |
|-------|--------------------|------------|
| ingestion | 2 | Disk I/O, network (yt-dlp) |
| transcription | 1 | CPU/GPU (Whisper) |
| scoring | 2 | CPU (ML signals) |
| rendering | 2 | CPU (FFmpeg) |
| publishing | 2 | Network (platform APIs) |

## Storage Layout

```
DATA_DIR/
  videos/         Raw downloaded video files ({id}.mp4)
  audio/          Extracted audio for Whisper ({id}.wav)
  rendered/       Final rendered clips ({id}.mp4)
  subtitles/      SRT and ASS subtitle files ({id}.srt, {id}.ass)
  thumbnails/     Generated thumbnail frames ({id}.jpg)
```

For production, set `USE_S3=true` and configure `S3_ENDPOINT_URL` + `S3_BUCKET`
to use S3-compatible object storage (AWS S3 or MinIO).

## Extension Points

### Adding a New Publishing Platform

1. Create `workers/adapters/<platform>.py` extending `PublishingAdapter`
2. Implement `upload(asset_path, metadata) -> platform_post_id`
3. Register in `workers/publishing.py` platform dispatch table
4. Add platform credentials to `infra/.env.example`
5. Add platform enum value to `PlatformType` in `app/db/models.py`
6. Create Alembic migration

### Adding a New Scoring Signal

1. Add signal function to `workers/scoring.py`
2. Store result in `clip_scores` table (signal_name, score, weight, explanation)
3. Update `SCORING_VERSION` in `app/core/config.py`
4. Document in scoring section of this file

### Adding a New LLM Provider

1. Create `libs/llm/<provider>.py` extending `LLMClient`
2. Implement `generate_copy(transcript, platform, context) -> CopyVariant`
3. Register in `workers/copy_gen.py` provider dispatch
4. Add `LLM_PROVIDER=<name>` to `.env.example`
