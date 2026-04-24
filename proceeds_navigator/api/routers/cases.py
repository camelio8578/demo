"""Case management endpoints."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from proceeds_navigator.api.deps import get_db
from proceeds_navigator.api.schemas import (
    CaseCreate,
    CaseDetail,
    CaseListResponse,
    CaseSummary,
    CaseUpdate,
)
from proceeds_navigator.db.models import Case, Lead

log = structlog.get_logger()
router = APIRouter(prefix="/cases", tags=["cases"])


def _generate_case_number(db: Session) -> str:
    year = datetime.utcnow().year
    count = db.scalar(
        select(func.count(Case.id)).where(
            Case.case_number.like(f"GS-{year}-%")
        )
    ) or 0
    return f"GS-{year}-{count + 1:04d}"


@router.get("", response_model=CaseListResponse)
def list_cases(
    county: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> CaseListResponse:
    q = select(Case)
    if county:
        q = q.where(Case.county == county)
    if stage:
        q = q.where(Case.stage == stage)

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(
        q.order_by(Case.claim_deadline.asc().nullslast(), Case.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return CaseListResponse(
        total=total or 0,
        page=page,
        page_size=page_size,
        items=[CaseSummary.model_validate(c) for c in items],
    )


@router.post("", response_model=CaseDetail, status_code=201)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)) -> CaseDetail:
    lead = db.get(Lead, payload.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.review_status != "qualified":
        raise HTTPException(
            status_code=422,
            detail=(
                "Lead must have review_status='qualified' before creating a case. "
                f"Current status: {lead.review_status}"
            ),
        )

    case_number = _generate_case_number(db)
    case = Case(
        lead_id=lead.id,
        case_number=case_number,
        client_name=payload.client_name,
        client_contact=payload.client_contact,
        county=lead.county,
        parcel_apn=lead.parcel_apn,
        claim_deadline=payload.claim_deadline,
        notes=payload.notes,
        stage="intake",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    log.info("case_created", case_number=case_number, lead_id=lead.id, county=lead.county)
    return CaseDetail.model_validate(case)


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(case_id: int, db: Session = Depends(get_db)) -> CaseDetail:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseDetail.model_validate(case)


@router.patch("/{case_id}", response_model=CaseDetail)
def update_case(
    case_id: int, update: CaseUpdate, db: Session = Depends(get_db)
) -> CaseDetail:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    for field, value in update.model_dump(exclude_none=True).items():
        setattr(case, field, value)

    db.commit()
    db.refresh(case)
    log.info("case_updated", case_id=case_id, stage=case.stage)
    return CaseDetail.model_validate(case)


@router.delete("/{case_id}", status_code=204)
def archive_case(case_id: int, db: Session = Depends(get_db)) -> None:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case.stage = "closed"
    db.commit()
    log.info("case_archived", case_id=case_id)
