# ClipOS

Autonomous short-form video clipping system.

## What it does

ClipOS monitors creator channels, ingests long-form videos, transcribes them,
identifies high-value clip candidates, renders short-form clips with subtitles,
generates platform-specific copy, and publishes — all with human-in-the-loop
review gates.

## Quick start

```bash
# 1. Clone and set up
./scripts/setup.sh

# 2. Edit environment
cp infra/.env.example infra/.env
$EDITOR infra/.env

# 3. Start services
cd infra && docker-compose up -d

# 4. Run migrations
docker-compose exec api alembic upgrade head

# 5. Seed demo data
API_URL=http://localhost:8000 ./scripts/seed.sh

# 6. Open API docs
open http://localhost:8000/docs

# 7. Monitor tasks
open http://localhost:5555
```

## Project structure

```
clipos/
  apps/
    api/         FastAPI backend (Python 3.11)
    admin/       Next.js operator dashboard (scaffold)
  workers/       Celery task workers
  libs/          Shared Python utilities
  infra/         Docker Compose, .env.example
  docs/          Architecture, API routes, credentials
  scripts/       setup.sh, seed.sh
  samples/       Sample video files (gitignored)
```

## Documentation

- [Architecture](docs/architecture.md)
- [API Routes](docs/api-routes.md)
- [Credential Checklist](docs/credential-checklist.md)
- [Roadmap](ROADMAP.md)

## Tech stack

| Layer | Choice |
|-------|--------|
| API | FastAPI + Pydantic v2 |
| Database | PostgreSQL + SQLAlchemy 2.0 + Alembic |
| Task queue | Celery + Redis |
| Downloader | yt-dlp |
| Audio | FFmpeg |
| Transcription | Whisper (via OpenAI or local) |
| Copy generation | OpenAI GPT / Anthropic Claude |
| Dashboard | Next.js 14 |
| Monitoring | Flower |
