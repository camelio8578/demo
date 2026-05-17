# ClipOS API Routes

Base URL: `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs`

## Creator Management

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/creators | Create creator |
| GET | /api/v1/creators | List creators |
| GET | /api/v1/creators/{id} | Get creator |
| PUT | /api/v1/creators/{id} | Update creator |
| DELETE | /api/v1/creators/{id} | Delete creator |
| POST | /api/v1/creators/{id}/platform-accounts | Add platform account |
| GET | /api/v1/creators/{id}/platform-accounts | List platform accounts |
| POST | /api/v1/creators/{id}/monitored-sources | Add source |
| GET | /api/v1/creators/{id}/monitored-sources | List sources |

## Rights Profiles

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/rights-profiles | Create profile |
| GET | /api/v1/rights-profiles | List profiles |
| GET | /api/v1/rights-profiles/{id} | Get profile |
| PUT | /api/v1/rights-profiles/{id} | Update profile |

## Ingestion

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/ingest | Ingest video URL |
| GET | /api/v1/videos | List videos |
| GET | /api/v1/videos/{id} | Get video |
| POST | /api/v1/videos/{id}/retranscribe | Re-queue transcription |

## Transcripts

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/videos/{id}/transcript | Get transcript |
| GET | /api/v1/videos/{id}/segments | Get segments |

## Candidates & Scoring

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/videos/{id}/candidates | List candidates |
| GET | /api/v1/candidates/{id} | Get candidate + scores |
| POST | /api/v1/candidates/{id}/score | Rescore candidate |
| PUT | /api/v1/candidates/{id}/status | Approve/reject |

## Rendering

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/candidates/{id}/render | Trigger render |
| GET | /api/v1/assets/{id} | Get asset |
| GET | /api/v1/assets/{id}/download | Download asset |
| POST | /api/v1/assets/{id}/rerender | Re-render |

## Copy Generation

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/candidates/{id}/copy | Generate copy |
| GET | /api/v1/candidates/{id}/copy | Get copy variants |
| PUT | /api/v1/copy/{id} | Update copy variant |

## Publishing

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/jobs | Create publishing job |
| GET | /api/v1/jobs | List jobs |
| GET | /api/v1/jobs/{id} | Get job + attempts |
| POST | /api/v1/jobs/{id}/retry | Retry job |
| DELETE | /api/v1/jobs/{id} | Cancel job |
| GET | /api/v1/jobs/queue-status | Queue depths |

## Review

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/review/queue | Review queue |
| POST | /api/v1/review/tasks | Create review task |
| GET | /api/v1/review/tasks | List tasks |
| PUT | /api/v1/review/tasks/{id} | Update task |

## Analytics

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/analytics/jobs/{job_id} | Get analytics |
| POST | /api/v1/analytics/ingest/{job_id} | Trigger analytics refresh |
| GET | /api/v1/analytics/summary | Creator summary |

## Webhooks (n8n compatible)

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/webhooks/ingest | Trigger full pipeline |

## Ops

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/health | System health |
| GET | /api/v1/health/workers | Worker health |

## Response Codes

| Code | Meaning |
|------|---------|
| 200 OK | Success |
| 201 Created | Resource created |
| 202 Accepted | Async job queued |
| 204 No Content | Soft delete succeeded |
| 400 Bad Request | Validation error |
| 404 Not Found | Resource missing |
| 409 Conflict | Slug/URL duplicate |
| 422 Unprocessable Entity | Business rule violation |
