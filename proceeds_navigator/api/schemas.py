"""Pydantic v2 schemas for FastAPI request/response models."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Lead Schemas ──────────────────────────────────────────────────────────────


class LeadSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    county: str
    source_type: str
    parcel_apn: Optional[str] = None
    situs_address: Optional[str] = None
    sale_date: Optional[date] = None
    excess_proceeds_amount: Optional[float] = None
    likely_claimant_type: str
    likely_claimant_name: Optional[str] = None
    score: Optional[float] = None
    priority_rank: Optional[int] = None
    legal_risk_flag: str
    review_status: str
    outreach_status: str
    created_at: datetime


class LeadDetail(LeadSummary):
    source_url: Optional[str] = None
    page_title: Optional[str] = None
    notice_date: Optional[date] = None
    board_item_id: Optional[str] = None
    excess_proceeds_signal: Optional[str] = None
    claimant_source_basis: Optional[str] = None
    score_explanation: Optional[dict[str, Any]] = None
    notes: Optional[str] = None
    last_checked_at: Optional[datetime] = None
    content_hash: Optional[str] = None
    updated_at: Optional[datetime] = None

    @field_validator("score_explanation", mode="before")
    @classmethod
    def parse_explanation(cls, v: Any) -> Optional[dict]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v


class LeadStatusUpdate(BaseModel):
    review_status: Optional[str] = None
    outreach_status: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("review_status")
    @classmethod
    def validate_review_status(cls, v: Optional[str]) -> Optional[str]:
        valid = {"pending", "reviewed", "qualified", "disqualified", "archived"}
        if v is not None and v not in valid:
            raise ValueError(f"review_status must be one of {valid}")
        return v

    @field_validator("outreach_status")
    @classmethod
    def validate_outreach_status(cls, v: Optional[str]) -> Optional[str]:
        valid = {"none", "drafted", "sent", "responded", "engaged", "closed"}
        if v is not None and v not in valid:
            raise ValueError(f"outreach_status must be one of {valid}")
        return v


class LeadListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[LeadSummary]


# ── Case Schemas ──────────────────────────────────────────────────────────────


class CaseCreate(BaseModel):
    lead_id: int
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    claim_deadline: Optional[date] = None
    notes: Optional[str] = None


class CaseSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_number: str
    lead_id: Optional[int] = None
    client_name: Optional[str] = None
    county: str
    parcel_apn: Optional[str] = None
    claim_deadline: Optional[date] = None
    stage: str
    fee_agreement_signed: bool
    created_at: datetime


class CaseDetail(CaseSummary):
    client_contact: Optional[str] = None
    outcome: Optional[str] = None
    notes: Optional[str] = None
    updated_at: Optional[datetime] = None


class CaseUpdate(BaseModel):
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    claim_deadline: Optional[date] = None
    stage: Optional[str] = None
    outcome: Optional[str] = None
    fee_agreement_signed: Optional[bool] = None
    notes: Optional[str] = None

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, v: Optional[str]) -> Optional[str]:
        valid = {"intake", "docs_gathering", "claim_prep", "filed", "resolved", "closed"}
        if v is not None and v not in valid:
            raise ValueError(f"stage must be one of {valid}")
        return v


class CaseListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[CaseSummary]


# ── Document Schemas ──────────────────────────────────────────────────────────


VALID_DOC_TYPES = {
    "outreach_intro", "outreach_followup", "intake_form",
    "document_checklist", "service_agreement", "claim_checklist", "case_summary",
}


class DocumentRequest(BaseModel):
    doc_type: str

    @field_validator("doc_type")
    @classmethod
    def validate_doc_type(cls, v: str) -> str:
        if v not in VALID_DOC_TYPES:
            raise ValueError(f"doc_type must be one of {VALID_DOC_TYPES}")
        return v


class DocumentRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    doc_type: str
    file_path: Optional[str] = None
    generated_at: datetime
    template_version: Optional[str] = None


# ── Health Schema ─────────────────────────────────────────────────────────────


class ScrapeRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    county: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    leads_found: int
    leads_new: int
    status: str


class HealthResponse(BaseModel):
    status: str
    version: str
    lead_count: int
    case_count: int
    last_scrape_runs: list[ScrapeRunSummary]
