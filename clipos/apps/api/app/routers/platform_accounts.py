"""Platform account endpoints, nested under creators."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Creator, CreatorPlatformAccount
from app.dependencies import get_db
from app.schemas.platform_accounts import (
    PlatformAccountCreate,
    PlatformAccountListResponse,
    PlatformAccountResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/creators", tags=["platform-accounts"])


def _get_creator_or_404(creator_id: uuid.UUID, db: Session) -> Creator:
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    return creator


@router.post("/{creator_id}/platform-accounts", response_model=PlatformAccountResponse, status_code=201)
def create_platform_account(
    creator_id: uuid.UUID,
    body: PlatformAccountCreate,
    db: Session = Depends(get_db),
) -> CreatorPlatformAccount:
    _get_creator_or_404(creator_id, db)

    account = CreatorPlatformAccount(
        id=uuid.uuid4(),
        creator_id=creator_id,
        platform=body.platform,
        platform_user_id=body.platform_user_id,
        channel_url=body.channel_url,
        display_name=body.display_name,
        access_token=body.access_token,
        refresh_token=body.refresh_token,
        token_expires_at=body.token_expires_at,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    logger.info("platform_account_created", account_id=str(account.id), creator_id=str(creator_id))
    return account


@router.get("/{creator_id}/platform-accounts", response_model=PlatformAccountListResponse)
def list_platform_accounts(
    creator_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> PlatformAccountListResponse:
    _get_creator_or_404(creator_id, db)
    items = (
        db.query(CreatorPlatformAccount)
        .filter(CreatorPlatformAccount.creator_id == creator_id)
        .all()
    )
    return PlatformAccountListResponse(items=items, total=len(items))
