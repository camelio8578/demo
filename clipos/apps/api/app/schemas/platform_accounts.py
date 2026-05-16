"""Pydantic v2 schemas for creator platform accounts."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PlatformAccountCreate(BaseModel):
    platform: str
    platform_user_id: Optional[str] = None
    channel_url: Optional[str] = None
    display_name: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None


class PlatformAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    creator_id: uuid.UUID
    platform: str
    platform_user_id: Optional[str] = None
    channel_url: Optional[str] = None
    display_name: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PlatformAccountListResponse(BaseModel):
    items: list[PlatformAccountResponse]
    total: int
