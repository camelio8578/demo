"""Pydantic v2 schemas for creators."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CreatorCreate(BaseModel):
    name: str
    slug: str
    rights_profile_id: Optional[uuid.UUID] = None


class CreatorUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    status: Optional[str] = None
    rights_profile_id: Optional[uuid.UUID] = None


class CreatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    status: str
    rights_profile_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class CreatorListResponse(BaseModel):
    items: list[CreatorResponse]
    total: int
