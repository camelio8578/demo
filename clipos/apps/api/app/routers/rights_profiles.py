"""Rights profile CRUD endpoints."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import RightsProfile
from app.dependencies import get_db
from app.schemas.rights_profiles import (
    RightsProfileCreate,
    RightsProfileListResponse,
    RightsProfileResponse,
    RightsProfileUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/rights-profiles", tags=["rights-profiles"])


@router.post("", response_model=RightsProfileResponse, status_code=201)
def create_rights_profile(
    body: RightsProfileCreate, db: Session = Depends(get_db)
) -> RightsProfile:
    profile = RightsProfile(
        id=uuid.uuid4(),
        name=body.name,
        allow_repost=body.allow_repost,
        require_attribution=body.require_attribution,
        commercial_use_allowed=body.commercial_use_allowed,
        manual_review_required=body.manual_review_required,
        risk_level=body.risk_level,
        notes=body.notes,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    logger.info("rights_profile_created", profile_id=str(profile.id))
    return profile


@router.get("", response_model=RightsProfileListResponse)
def list_rights_profiles(db: Session = Depends(get_db)) -> RightsProfileListResponse:
    items = db.query(RightsProfile).all()
    return RightsProfileListResponse(items=items, total=len(items))


@router.get("/{profile_id}", response_model=RightsProfileResponse)
def get_rights_profile(
    profile_id: uuid.UUID, db: Session = Depends(get_db)
) -> RightsProfile:
    profile = db.query(RightsProfile).filter(RightsProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Rights profile not found")
    return profile


@router.put("/{profile_id}", response_model=RightsProfileResponse)
def update_rights_profile(
    profile_id: uuid.UUID, body: RightsProfileUpdate, db: Session = Depends(get_db)
) -> RightsProfile:
    profile = db.query(RightsProfile).filter(RightsProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Rights profile not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    logger.info("rights_profile_updated", profile_id=str(profile_id))
    return profile
