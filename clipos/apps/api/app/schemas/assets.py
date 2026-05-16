"""Pydantic v2 schemas for rendered assets."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RenderedAssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_clip_id: uuid.UUID
    output_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    resolution: Optional[str] = None
    fps: Optional[int] = None
    duration_seconds: Optional[float] = None
    render_job_id: Optional[str] = None
    status: str
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RenderRequest(BaseModel):
    """Optional overrides for the render job."""
    padding_seconds: float = 1.5
    priority: int = 5  # 1 = highest


class ReRenderRequest(BaseModel):
    """Request body for re-queuing a render."""
    force: bool = False
    padding_seconds: float = 1.5
