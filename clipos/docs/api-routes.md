# ClipOS API Routes

Base URL: `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs`

## Health

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/health | System health: db_ok, redis_ok, version |

## Rights Profiles

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/rights-profiles | Create rights profile |
| GET | /api/v1/rights-profiles | List all rights profiles |
| GET | /api/v1/rights-profiles/{id} | Get one rights profile |
| PUT | /api/v1/rights-profiles/{id} | Update rights profile |

## Creators

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/creators | Create creator |
| GET | /api/v1/creators | List creators (filter: ?status=active) |
| GET | /api/v1/creators/{id} | Get one creator |
| PUT | /api/v1/creators/{id} | Update creator |
| DELETE | /api/v1/creators/{id} | Soft-delete (sets status=blocked) |

## Platform Accounts

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/creators/{id}/platform-accounts | Add platform account |
| GET | /api/v1/creators/{id}/platform-accounts | List platform accounts |

## Monitored Sources

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/creators/{id}/monitored-sources | Add monitored source |
| GET | /api/v1/creators/{id}/monitored-sources | List monitored sources |

## Ingestion

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/ingest | Trigger video ingestion; returns job_id |
| GET | /api/v1/videos | List source videos (filter: ?status=&creator_id=) |
| GET | /api/v1/videos/{id} | Get video with transcript status |
| POST | /api/v1/videos/{id}/retranscribe | Re-queue transcription for a video |

## Response codes

- 201 Created — resource created
- 202 Accepted — async job queued
- 204 No Content — soft delete succeeded
- 400 Bad Request — validation error
- 404 Not Found — resource missing
- 409 Conflict — slug/URL duplicate
- 422 Unprocessable Entity — business rule violation
