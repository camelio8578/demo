"""Pydantic schemas for analytics snapshots and summaries."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AnalyticsSnapshotOut(BaseModel):
    id: uuid.UUID
    publishing_job_id: uuid.UUID
    snapshot_at: datetime
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    saves: Optional[int] = None
    watch_time_seconds: Optional[int] = None
    completion_rate: Optional[float] = None
    platform_raw: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreatorPerformanceSummary(BaseModel):
    creator_id: uuid.UUID
    creator_name: str
    total_published_clips: int
    avg_views: float
    avg_likes: float
    avg_completion_rate: Optional[float] = None
    top_clip_id: Optional[uuid.UUID] = None
    top_clip_views: Optional[int] = None


class AnalyticsSummaryOut(BaseModel):
    """Creator-level performance summary across all published clips."""

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    total_snapshots: int
    total_published_jobs: int
    creators: list[CreatorPerformanceSummary] = Field(default_factory=list)
    platform_breakdown: dict[str, int] = Field(
        default_factory=dict,
        description="Total views per platform",
    )
