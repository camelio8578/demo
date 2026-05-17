"""Monitored source endpoints, nested under creators."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Creator, MonitoredSource
from app.dependencies import get_db
from app.schemas.monitored_sources import (
    MonitoredSourceCreate,
    MonitoredSourceListResponse,
    MonitoredSourceResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/creators", tags=["monitored-sources"])


def _get_creator_or_404(creator_id: uuid.UUID, db: Session) -> Creator:
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    return creator


@router.post(
    "/{creator_id}/monitored-sources",
    response_model=MonitoredSourceResponse,
    status_code=201,
)
def create_monitored_source(
    creator_id: uuid.UUID,
    body: MonitoredSourceCreate,
    db: Session = Depends(get_db),
) -> MonitoredSource:
    _get_creator_or_404(creator_id, db)

    source = MonitoredSource(
        id=uuid.uuid4(),
        creator_id=creator_id,
        platform=body.platform,
        source_url=body.source_url,
        source_identifier=body.source_identifier,
        polling_interval_minutes=body.polling_interval_minutes,
        enabled=body.enabled,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    logger.info(
        "monitored_source_created",
        source_id=str(source.id),
        creator_id=str(creator_id),
    )
    return source


@router.get(
    "/{creator_id}/monitored-sources",
    response_model=MonitoredSourceListResponse,
)
def list_monitored_sources(
    creator_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> MonitoredSourceListResponse:
    _get_creator_or_404(creator_id, db)
    items = (
        db.query(MonitoredSource)
        .filter(MonitoredSource.creator_id == creator_id)
        .all()
    )
    return MonitoredSourceListResponse(items=items, total=len(items))
