# ClipOS — Autonomous Short-Form Clipping OS

Turn any long-form video into platform-ready short clips automatically: monitor → ingest → transcribe → score → render → publish.

## What It Does

ClipOS is an operator-run pipeline that:

1. **Monitors** creator channels for new long-form content
2. **Ingests** videos via yt-dlp (YouTube, TikTok, and more)
3. **Transcribes** speech with Whisper (runs locally, no API key needed)
4. **Scores** candidate clips using 9 heuristic signals (hook phrases, speech density, sentiment, pause/burst patterns, duration fit)
5. **Renders** short-form clips with FFmpeg: 9:16 reframe, subtitle burn-in, thumbnail
6. **Generates** platform-specific copy (hook, title, caption, hashtags) via LLM or rule-based fallback
7. **Publishes** to YouTube Shorts, TikTok, and Instagram Reels via platform APIs (credentials required)

Everything except platform publishing runs fully offline with no external API keys.

## Architecture Overview

```
Creator Channel (YouTube / TikTok / Instagram)
        │
        ▼
MonitoredSource polling (Celery beat)
        │  source_url
        ▼
POST /api/v1/ingest  ──→  Redis (Celery broker)
                                │
              ┌─────────────────┼─────────────────────┐
              ▼                 ▼                       ▼
      queue:ingestion   queue:transcription     queue:scoring
      yt-dlp + ffmpeg      Whisper STT          9-signal scorer
              │                 │                       │
              └────────→ PostgreSQL ←──────────────────┘
                                │
                    ┌───────────┴────────────┐
                    ▼                        ▼
            queue:rendering           queue:scoring
            FFmpeg clip render     LLM copy generation
                    │
                    ▼
            queue:publishing
            YouTube / TikTok / Instagram
```

## Quick Start

```bash
# 1. Clone the repo and run setup
git clone <repo-url>
cd clipos
bash scripts/setup.sh

# 2. Edit environment (set SECRET_KEY at minimum)
cp infra/.env.example infra/.env
$EDITOR infra/.env

# 3. Start all services
docker-compose -f infra/docker-compose.yml up -d

# 4. Run database migrations
docker-compose -f infra/docker-compose.yml exec api alembic upgrade head

# 5. Run the seed demo
bash scripts/seed.sh
```

Then open:
- Admin UI: http://localhost:3001
- API docs: http://localhost:8000/docs
- Flower (job monitor): http://localhost:5555

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Docker | 24+ | Required for Compose |
| Docker Compose | v2 | Included with Docker Desktop |
| ffmpeg | Any | Only needed for local dev (inside Docker otherwise) |
| Python | 3.11+ | Only needed for local dev outside Docker |

## Installation

### Docker (recommended)

```bash
bash scripts/setup.sh
```

This script:
- Checks for Docker and Python
- Copies `infra/.env.example` to `infra/.env` if missing
- Creates a Python virtual environment in `apps/api/.venv`
- Installs Python dependencies

### Local Dev (no Docker)

```bash
bash scripts/run_local.sh
```

Requires PostgreSQL and Redis running locally. Reads connection strings from `infra/.env`.

## Configuration

### Required Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL DSN (set automatically in Docker Compose) |
| `REDIS_URL` | Redis URL (set automatically in Docker Compose) |
| `SECRET_KEY` | Random secret for session signing (`openssl rand -hex 32`) |
| `DATA_DIR` | Absolute path for video/audio/rendered asset storage |

### Optional — Whisper Model

| Variable | Default | Options |
|----------|---------|---------|
| `WHISPER_MODEL` | `base` | `tiny`, `base`, `small`, `medium`, `large-v3` |

Use `tiny` or `base` for development speed. Use `medium` or `large-v3` for production quality.

### Optional — LLM Enhancement

| Variable | Description |
|----------|-------------|
| `LLM_PROVIDER` | `none` (default), `openai`, or `anthropic` |
| `OPENAI_API_KEY` | Required if `LLM_PROVIDER=openai` |
| `ANTHROPIC_API_KEY` | Required if `LLM_PROVIDER=anthropic` |

### Optional — Platform Publishing

See [docs/credential-checklist.md](docs/credential-checklist.md) for full setup steps.

| Variable | Platform |
|----------|----------|
| `YOUTUBE_API_KEY`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` | YouTube Shorts |
| `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_ACCESS_TOKEN` | TikTok |
| `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_ACCOUNT_ID` | Instagram Reels |

### Optional — Cloud Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_S3` | `false` | Enable S3/MinIO instead of local filesystem |
| `S3_ENDPOINT_URL` | — | MinIO or AWS S3 endpoint |
| `S3_BUCKET` | — | Bucket name |
| `AWS_ACCESS_KEY_ID` | — | S3 credentials |
| `AWS_SECRET_ACCESS_KEY` | — | S3 credentials |

### Pipeline Tuning

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_CLIP_DURATION` | `30` | Minimum candidate clip length (seconds) |
| `MAX_CLIP_DURATION` | `120` | Maximum candidate clip length (seconds) |
| `CLIP_PADDING_SECONDS` | `1.5` | Padding added before/after clip boundaries |
| `MAX_CANDIDATES_PER_VIDEO` | `10` | Max scored candidates stored per video |
| `AUTO_RENDER_TOP_N` | `5` | Auto-render top N candidates if enabled |
| `AUTO_RENDER_ENABLED` | `false` | Automatically render without human approval |

## Running the Demo

The seed script demonstrates the full pipeline end-to-end:

```bash
# Default: uses a public YouTube video
bash scripts/seed.sh

# Custom video
bash scripts/seed.sh "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"

# Custom video + creator name
bash scripts/seed.sh "https://www.youtube.com/watch?v=YOUR_VIDEO_ID" "My Creator"
```

The script will:
1. Wait for the API to be ready
2. Create a rights profile
3. Create a demo creator
4. Trigger video ingestion
5. Print monitoring URLs

Monitor pipeline progress at http://localhost:5555 (Flower).

## API Reference

Full route list: [docs/api-routes.md](docs/api-routes.md)

Interactive docs with request/response schemas: http://localhost:8000/docs

Key endpoints:

```bash
# Health check
GET  /api/v1/health

# Create a creator
POST /api/v1/creators

# Ingest a video
POST /api/v1/ingest

# List scored candidates for a video
GET  /api/v1/videos/{id}/candidates

# Approve a candidate for rendering
PUT  /api/v1/candidates/{id}/status   body: {"status": "approved"}

# Trigger render
POST /api/v1/candidates/{id}/render

# Generate copy
POST /api/v1/candidates/{id}/copy

# Create publishing job
POST /api/v1/jobs
```

## Admin Dashboard

The operator dashboard runs at http://localhost:3001.

From the dashboard you can:
- Manage creators and rights profiles
- Review scored clip candidates
- Preview rendered clips
- Approve or reject candidates
- Monitor publishing job status
- View analytics snapshots

## Worker Jobs

All async work runs in Celery. Each queue has a dedicated worker container.

| Queue | Task | Description |
|-------|------|-------------|
| `ingestion` | `ingest_video_task` | yt-dlp metadata fetch + download + ffmpeg audio extract |
| `transcription` | `transcribe_video_task` | Whisper speech-to-text, segment storage |
| `scoring` | `score_candidates_task` | 9-signal heuristic scoring, candidate creation |
| `scoring` | `generate_copy_task` | LLM or rule-based copy generation |
| `scoring` | `analytics_refresh_task` | Platform analytics snapshot ingestion |
| `rendering` | `render_clip_task` | FFmpeg clip extraction, 9:16 reframe, subtitle burn-in |
| `publishing` | `publish_clip_task` | Platform API upload with retry |

Monitor all queues and task results at http://localhost:5555 (Flower).

## What Works Locally

No credentials required for these features:

- Video ingestion (yt-dlp downloads from YouTube and 1000+ sites)
- Speech transcription (Whisper runs on CPU locally)
- Candidate scoring (9 heuristic signals, fully local)
- Clip rendering (FFmpeg: extract, reframe, subtitle burn-in)
- Caption and subtitle generation
- Rule-based copy generation (title, caption, hashtag templates)
- Admin review dashboard
- All API endpoints
- All database operations

## What Requires Credentials

| Feature | Required Credentials |
|---------|---------------------|
| YouTube Shorts publishing | Google Cloud OAuth app + YouTube Data API v3 |
| TikTok publishing | TikTok Developer app (requires approval) |
| Instagram Reels publishing | Meta Developer app (requires App Review) |
| LLM-quality copy | `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` |
| YouTube analytics | `YOUTUBE_API_KEY` |
| Cloud asset storage | S3 or MinIO credentials |

See [docs/credential-checklist.md](docs/credential-checklist.md) for step-by-step setup.

## Adding a New Platform

To add a new publishing platform (e.g. LinkedIn, Twitter/X):

1. Create `workers/adapters/<platform>.py`:

```python
from workers.adapters.base import PublishingAdapter

class LinkedInAdapter(PublishingAdapter):
    async def upload(self, asset_path: str, metadata: dict) -> str:
        """Upload clip and return platform post ID."""
        ...
        return platform_post_id
```

2. Register in `workers/publishing.py` dispatch table:

```python
ADAPTERS = {
    "youtube": YouTubeAdapter,
    "tiktok": TikTokAdapter,
    "instagram": InstagramAdapter,
    "linkedin": LinkedInAdapter,  # add here
}
```

3. Add `PlatformType.linkedin` to `app/db/models.py` enum.

4. Run `alembic revision --autogenerate -m "add linkedin platform"` and `alembic upgrade head`.

5. Add credentials to `infra/.env.example` and document in `docs/credential-checklist.md`.

## Development

### Local Run (without Docker)

```bash
# Requires: PostgreSQL + Redis running locally
bash scripts/run_local.sh
```

### Docker Compose (recommended)

```bash
cd clipos
docker-compose -f infra/docker-compose.yml up -d
docker-compose -f infra/docker-compose.yml logs -f api
```

### Database Migrations

```bash
# After editing apps/api/app/db/models.py:
docker-compose -f infra/docker-compose.yml exec api alembic revision --autogenerate -m "description"
docker-compose -f infra/docker-compose.yml exec api alembic upgrade head
```

### Running Tests

```bash
cd apps/api
pytest tests/ -v
```

## Project Structure

```
clipos/
  apps/
    api/           FastAPI backend (Python 3.11)
      app/         Application code
      Dockerfile
      requirements.txt
    admin/         Next.js 14 operator dashboard
      src/
      Dockerfile
  workers/         Celery task workers
  libs/            Shared Python utilities
  infra/           Docker Compose + .env.example
  docs/            Architecture, API routes, credential checklist
  scripts/         setup.sh, seed.sh, run_local.sh
  samples/         Sample video fixtures (gitignored binaries)
```

## Documentation

- [Architecture](docs/architecture.md) — System diagram, data flow, queue routing
- [API Routes](docs/api-routes.md) — Complete endpoint reference
- [Credential Checklist](docs/credential-checklist.md) — Platform API setup guides
- [Roadmap](ROADMAP.md) — MVP status and future phases
