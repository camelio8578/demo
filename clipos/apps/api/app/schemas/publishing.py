"""Pydantic schemas for publishing jobs and webhooks."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Publishing Job Schemas
# ---------------------------------------------------------------------------


class PublishingJobCreate(BaseModel):
    rendered_asset_id: uuid.UUID
    copy_variant_id: uuid.UUID
    publishing_target_id: uuid.UUID
    scheduled_at: Optional[datetime] = None


class PublishAttemptOut(BaseModel):
    id: uuid.UUID
    publishing_job_id: uuid.UUID
    attempt_number: int
    attempted_at: datetime
    status: str
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    failure_reason: Optional[str] = None

    model_config = {"from_attributes": True}


class PublishingJobOut(BaseModel):
    id: uuid.UUID
    rendered_asset_id: uuid.UUID
    copy_variant_id: uuid.UUID
    publishing_target_id: uuid.UUID
    status: str
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    platform_post_id: Optional[str] = None
    failure_reason: Optional[str] = None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    publish_attempts: list[PublishAttemptOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Queue Status Schema
# ---------------------------------------------------------------------------


class QueueCounts(BaseModel):
    ingestion: int = 0
    transcription: int = 0
    scoring: int = 0
    rendering: int = 0
    publishing: int = 0


class QueueStatus(BaseModel):
    queued_jobs: QueueCounts
    active_workers: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Webhook Schema (n8n-compatible entry point)
# ---------------------------------------------------------------------------


class WebhookIngestRequest(BaseModel):
    """
    Webhook payload accepted at POST /api/v1/webhooks/ingest.

    This is the n8n-compatible entry point for triggering the full
    ClipOS pipeline from an external automation.

    Fields:
    - source_url: The URL of the video to ingest (required).
    - creator_id: UUID of the creator this video belongs to (required).
    - auto_render: If True, automatically queue rendering after scoring (default False).
    - auto_publish: If True, automatically queue publishing after rendering (default False).
      Requires a publishing_target_id if True.
    - publishing_target_id: Required when auto_publish=True.
    - force_redownload: If True, re-queue even if video already ingested.

    Example n8n HTTP Request node payload:
        {
          "source_url": "https://youtube.com/watch?v=...",
          "creator_id": "123e4567-e89b-12d3-a456-426614174000",
          "auto_render": true,
          "auto_publish": false
        }
    """

    source_url: str = Field(..., description="URL of the video to ingest")
    creator_id: uuid.UUID = Field(..., description="Creator UUID")
    auto_render: bool = Field(
        default=False,
        description="Automatically queue rendering after scoring completes",
    )
    auto_publish: bool = Field(
        default=False,
        description="Automatically queue publishing after rendering completes",
    )
    publishing_target_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Required when auto_publish=True",
    )
    force_redownload: bool = Field(
        default=False,
        description="Re-queue even if video URL was already ingested",
    )


class WebhookIngestResponse(BaseModel):
    job_id: str
    source_video_id: uuid.UUID
    message: str
    pipeline_flags: dict
