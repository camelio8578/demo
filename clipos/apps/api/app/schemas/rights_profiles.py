"""Pydantic v2 schemas for rights profiles."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RightsProfileCreate(BaseModel):
    name: str
    allow_repost: bool = False
    require_attribution: bool = False
    commercial_use_allowed: bool = False
    manual_review_required: bool = False
    risk_level: str = "medium"
    notes: Optional[str] = None


class RightsProfileUpdate(BaseModel):
    name: Optional[str] = None
    allow_repost: Optional[bool] = None
    require_attribution: Optional[bool] = None
    commercial_use_allowed: Optional[bool] = None
    manual_review_required: Optional[bool] = None
    risk_level: Optional[str] = None
    notes: Optional[str] = None


class RightsProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    allow_repost: bool
    require_attribution: bool
    commercial_use_allowed: bool
    manual_review_required: bool
    risk_level: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RightsProfileListResponse(BaseModel):
    items: list[RightsProfileResponse]
    total: int
