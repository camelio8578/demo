"""Creator CRUD endpoints."""

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models import Creator
from app.dependencies import get_db
from app.schemas.creators import (
    CreatorCreate,
    CreatorListResponse,
    CreatorResponse,
    CreatorUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/creators", tags=["creators"])


@router.post("", response_model=CreatorResponse, status_code=201)
def create_creator(body: CreatorCreate, db: Session = Depends(get_db)) -> Creator:
    existing = db.query(Creator).filter(Creator.slug == body.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Slug '{body.slug}' already taken")

    creator = Creator(
        id=uuid.uuid4(),
        name=body.name,
        slug=body.slug,
        rights_profile_id=body.rights_profile_id,
    )
    db.add(creator)
    db.commit()
    db.refresh(creator)
    logger.info("creator_created", creator_id=str(creator.id), slug=creator.slug)
    return creator


@router.get("", response_model=CreatorListResponse)
def list_creators(
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
) -> CreatorListResponse:
    q = db.query(Creator)
    if status:
        q = q.filter(Creator.status == status)
    items = q.all()
    return CreatorListResponse(items=items, total=len(items))


@router.get("/{creator_id}", response_model=CreatorResponse)
def get_creator(creator_id: uuid.UUID, db: Session = Depends(get_db)) -> Creator:
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    return creator


@router.put("/{creator_id}", response_model=CreatorResponse)
def update_creator(
    creator_id: uuid.UUID, body: CreatorUpdate, db: Session = Depends(get_db)
) -> Creator:
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    if body.name is not None:
        creator.name = body.name
    if body.slug is not None:
        existing = (
            db.query(Creator)
            .filter(Creator.slug == body.slug, Creator.id != creator_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail=f"Slug '{body.slug}' already taken")
        creator.slug = body.slug
    if body.status is not None:
        creator.status = body.status
    if body.rights_profile_id is not None:
        creator.rights_profile_id = body.rights_profile_id

    db.commit()
    db.refresh(creator)
    logger.info("creator_updated", creator_id=str(creator_id))
    return creator


@router.delete("/{creator_id}", status_code=204)
def delete_creator(creator_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    creator.status = "blocked"
    db.commit()
    logger.info("creator_soft_deleted", creator_id=str(creator_id))
