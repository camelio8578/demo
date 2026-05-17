"""Pydantic v2 schemas for monitored sources."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MonitoredSourceCreate(BaseModel):
    platform: str
    source_url: str
    source_identifier: Optional[str] = None
    polling_interval_minutes: int = 60
    enabled: bool = True


class MonitoredSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    creator_id: uuid.UUID
    platform: str
    source_url: str
    source_identifier: Optional[str] = None
    polling_interval_minutes: int
    last_polled_at: Optional[datetime] = None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class MonitoredSourceListResponse(BaseModel):
    items: list[MonitoredSourceResponse]
    total: int
