"""Pydantic v2 schemas for copy variants."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class CopyVariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_clip_id: uuid.UUID
    platform: str
    variant_index: int
    hook: Optional[str] = None
    title: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[list[str]] = None
    llm_model_used: Optional[str] = None
    prompt_version: Optional[str] = None
    created_at: datetime


class CopyVariantListOut(BaseModel):
    items: list[CopyVariantOut]
    total: int


class CopyVariantUpdate(BaseModel):
    """Body for human edits to a copy variant."""
    hook: Optional[str] = None
    title: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[list[str]] = None


class CopyGenerateRequest(BaseModel):
    """Trigger copy generation for specific platforms."""
    platforms: list[str] = ["tiktok", "instagram", "youtube"]
    llm_provider: str = "none"
