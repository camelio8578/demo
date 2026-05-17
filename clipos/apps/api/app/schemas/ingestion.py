"""Pydantic v2 schemas for ingestion endpoints."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class IngestRequest(BaseModel):
    source_url: str
    creator_id: uuid.UUID
    force_redownload: bool = False


class IngestResponse(BaseModel):
    job_id: str
    source_video_id: Optional[uuid.UUID] = None
    message: str


class TranscriptStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    model_used: Optional[str] = None
    language: str
    word_count: Optional[int] = None
    failure_reason: Optional[str] = None
    created_at: datetime


class SourceVideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    creator_id: uuid.UUID
    monitored_source_id: Optional[uuid.UUID] = None
    platform_video_id: Optional[str] = None
    title: Optional[str] = None
    source_url: str
    duration_seconds: Optional[float] = None
    published_at: Optional[datetime] = None
    downloaded_at: Optional[datetime] = None
    local_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    status: str
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    transcripts: list[TranscriptStatusResponse] = []


class SourceVideoListResponse(BaseModel):
    items: list[SourceVideoResponse]
    total: int


class RetranscribeResponse(BaseModel):
    job_id: str
    message: str
