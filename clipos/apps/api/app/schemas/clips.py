"""Pydantic v2 schemas for candidate clips and scores."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ClipScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_clip_id: uuid.UUID
    total_score: float
    speech_density: float
    sentiment_score: float
    hook_phrase_score: float
    pause_burst_score: float
    novelty_score: float
    completeness_score: float
    duration_fit_score: float
    risk_flag_score: float
    prior_performance_score: float
    llm_rescore: Optional[float] = None
    scoring_version: str
    created_at: datetime


class CandidateClipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_video_id: uuid.UUID
    transcript_id: Optional[uuid.UUID] = None
    start_time: float
    end_time: float
    duration_seconds: float
    segment_text: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    scores: list[ClipScoreOut] = []


class CandidateClipListOut(BaseModel):
    items: list[CandidateClipOut]
    total: int


class CandidateStatusUpdate(BaseModel):
    status: str  # approved | rejected | candidate
    notes: Optional[str] = None


class RescoreResponse(BaseModel):
    job_id: str
    candidate_clip_id: uuid.UUID
    message: str
