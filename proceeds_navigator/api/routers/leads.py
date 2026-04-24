"""Lead management endpoints."""

from __future__ import annotations

import json
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from proceeds_navigator.api.deps import get_db
from proceeds_navigator.api.schemas import (
    LeadDetail,
    LeadListResponse,
    LeadStatusUpdate,
    LeadSummary,
)
from proceeds_navigator.db.models import Lead
from proceeds_navigator.scoring.scorer import LeadScorer
from proceeds_navigator.scoring.explainer import explanation_to_json

log = structlog.get_logger()
router = APIRouter(prefix="/leads", tags=["leads"])

_scorer = LeadScorer()


@router.get("", response_model=LeadListResponse)
def list_leads(
    county: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    outreach_status: Optional[str] = Query(None),
    legal_risk_flag: Optional[str] = Query(None),
    score_min: Optional[float] = Query(None, ge=0, le=100),
    score_max: Optional[float] = Query(None, ge=0, le=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> LeadListResponse:
    q = select(Lead)
    if county:
        q = q.where(Lead.county == county)
    if review_status:
        q = q.where(Lead.review_status == review_status)
    if outreach_status:
        q = q.where(Lead.outreach_status == outreach_status)
    if legal_risk_flag:
        q = q.where(Lead.legal_risk_flag == legal_risk_flag)
    if score_min is not None:
        q = q.where(Lead.score >= score_min)
    if score_max is not None:
        q = q.where(Lead.score <= score_max)

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(
        q.order_by(Lead.priority_rank.asc().nullslast(), Lead.score.desc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return LeadListResponse(
        total=total or 0,
        page=page,
        page_size=page_size,
        items=[LeadSummary.model_validate(item) for item in items],
    )


@router.get("/{lead_id}", response_model=LeadDetail)
def get_lead(lead_id: int, db: Session = Depends(get_db)) -> LeadDetail:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadDetail.model_validate(lead)


@router.patch("/{lead_id}/status", response_model=LeadDetail)
def update_lead_status(
    lead_id: int,
    update: LeadStatusUpdate,
    db: Session = Depends(get_db),
) -> LeadDetail:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    old_review = lead.review_status
    old_outreach = lead.outreach_status

    if update.review_status is not None:
        lead.review_status = update.review_status
    if update.outreach_status is not None:
        lead.outreach_status = update.outreach_status
    if update.notes is not None:
        lead.notes = update.notes

    db.commit()
    db.refresh(lead)

    log.info(
        "lead_status_updated",
        lead_id=lead_id,
        review_status=f"{old_review} → {lead.review_status}",
        outreach_status=f"{old_outreach} → {lead.outreach_status}",
    )
    return LeadDetail.model_validate(lead)


@router.get("/{lead_id}/score", response_model=LeadDetail)
def rescore_lead(lead_id: int, db: Session = Depends(get_db)) -> LeadDetail:
    """Recompute score for a lead and persist the result."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_dict = {
        "county": lead.county,
        "source_type": lead.source_type,
        "parcel_apn": lead.parcel_apn,
        "excess_proceeds_amount": lead.excess_proceeds_amount,
        "excess_proceeds_signal": lead.excess_proceeds_signal,
        "likely_claimant_type": lead.likely_claimant_type,
        "likely_claimant_name": lead.likely_claimant_name,
        "sale_date": lead.sale_date,
    }
    result = _scorer.score(lead_dict)
    lead.score = result.score
    lead.priority_rank = result.priority_rank
    lead.legal_risk_flag = result.legal_risk_flag
    lead.score_explanation = explanation_to_json(result.explanation)

    db.commit()
    db.refresh(lead)
    log.info("lead_rescored", lead_id=lead_id, score=result.score, rank=result.priority_rank)
    return LeadDetail.model_validate(lead)
