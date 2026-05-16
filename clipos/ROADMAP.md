# ClipOS Roadmap

## Phase 1 — Repo Scaffolding (complete)
- Directory structure
- Admin Next.js scaffold
- Documentation stubs

## Phase 2 — Database Schema (complete)
- 20 SQLAlchemy models with full relationships
- Alembic migration setup
- PostgreSQL enums for all status fields

## Phase 3 — Creator & Source Registration APIs (complete)
- Rights profiles CRUD
- Creators CRUD (soft-delete)
- Platform accounts (nested under creator)
- Monitored sources (nested under creator)
- Pydantic v2 request/response schemas

## Phase 4 — Ingestion Pipeline (complete)
- POST /api/v1/ingest → Celery task dispatch
- ingest_video_task: yt-dlp metadata + download + ffmpeg audio extract
- transcribe_video_task: status tracking stub (chains to transcription worker)
- Video list + detail + retranscribe endpoints

## Phase 5 — Transcription Worker (planned)
- Whisper local transcription
- OpenAI Whisper API fallback
- Transcript segment storage
- Word-level timestamps

## Phase 6 — Clip Scoring (planned)
- Speech density scoring
- Sentiment analysis
- Hook phrase detection
- Pause/burst detection
- Duration fit scoring
- LLM rescore option

## Phase 7 — Rendering Pipeline (planned)
- FFmpeg clip extraction
- Subtitle generation (SRT + ASS)
- Subtitle burn-in
- Thumbnail generation
- Resolution normalization (9:16 for Shorts/TikTok/Reels)

## Phase 8 — Copy Generation (planned)
- Platform-specific hook/title/caption/hashtags
- OpenAI GPT or Anthropic Claude
- Variant generation (A/B testing)

## Phase 9 — Publishing (planned)
- YouTube Shorts API
- TikTok Content Posting API
- Instagram Reels API
- Retry logic with exponential backoff

## Phase 10 — Analytics (planned)
- Scheduled analytics snapshots
- Performance feedback loop to scoring
- Experiment framework

## Phase 11 — Admin Dashboard (planned)
- Creator management UI
- Clip review queue
- Publishing schedule
- Analytics charts
