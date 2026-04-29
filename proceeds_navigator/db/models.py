"""SQLAlchemy ORM models for Proceeds Navigator."""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ── Enumerations ──────────────────────────────────────────────────────────────


class County(str, enum.Enum):
    fresno = "fresno"
    san_diego = "san_diego"
    sacramento = "sacramento"
    los_angeles = "los_angeles"


class SourceType(str, enum.Enum):
    auction_list = "auction_list"
    agenda_item = "agenda_item"
    notice = "notice"
    press_release = "press_release"
    web_page = "web_page"


class ClaimantType(str, enum.Enum):
    former_owner = "former_owner"
    lienholder = "lienholder"
    unknown = "unknown"


class RiskFlag(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    requires_legal_review = "REQUIRES_LEGAL_REVIEW"


class ReviewStatus(str, enum.Enum):
    pending = "pending"
    reviewed = "reviewed"
    qualified = "qualified"
    disqualified = "disqualified"
    archived = "archived"


class OutreachStatus(str, enum.Enum):
    none = "none"
    drafted = "drafted"
    sent = "sent"
    responded = "responded"
    engaged = "engaged"
    closed = "closed"


class CaseStage(str, enum.Enum):
    intake = "intake"
    docs_gathering = "docs_gathering"
    claim_prep = "claim_prep"
    filed = "filed"
    resolved = "resolved"
    closed = "closed"


class DocType(str, enum.Enum):
    outreach_intro = "outreach_intro"
    outreach_followup = "outreach_followup"
    intake_form = "intake_form"
    document_checklist = "document_checklist"
    service_agreement = "service_agreement"
    claim_checklist = "claim_checklist"
    case_summary = "case_summary"


class ScrapeRunStatus(str, enum.Enum):
    success = "success"
    partial = "partial"
    failed = "failed"


# ── Models ────────────────────────────────────────────────────────────────────


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    county: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    page_title: Mapped[Optional[str]] = mapped_column(Text)
    parcel_apn: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    situs_address: Mapped[Optional[str]] = mapped_column(Text)
    sale_date: Mapped[Optional[date]] = mapped_column(Date)
    notice_date: Mapped[Optional[date]] = mapped_column(Date)
    board_item_id: Mapped[Optional[str]] = mapped_column(String(100))
    excess_proceeds_signal: Mapped[Optional[str]] = mapped_column(Text)
    excess_proceeds_amount: Mapped[Optional[float]] = mapped_column(Float)
    likely_claimant_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ClaimantType.unknown.value
    )
    likely_claimant_name: Mapped[Optional[str]] = mapped_column(Text)
    claimant_source_basis: Mapped[Optional[str]] = mapped_column(Text)
    priority_rank: Mapped[Optional[int]] = mapped_column(Integer)
    score: Mapped[Optional[float]] = mapped_column(Float)
    score_explanation: Mapped[Optional[str]] = mapped_column(Text)  # JSON
    legal_risk_flag: Mapped[str] = mapped_column(
        String(50), nullable=False, default=RiskFlag.medium.value
    )
    review_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ReviewStatus.pending.value, index=True
    )
    outreach_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=OutreachStatus.none.value
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    cases: Mapped[list[Case]] = relationship("Case", back_populates="lead")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("leads.id"))
    case_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    client_name: Mapped[Optional[str]] = mapped_column(Text)
    client_contact: Mapped[Optional[str]] = mapped_column(Text)
    county: Mapped[str] = mapped_column(String(50), nullable=False)
    parcel_apn: Mapped[Optional[str]] = mapped_column(String(50))
    claim_deadline: Mapped[Optional[date]] = mapped_column(Date)
    stage: Mapped[str] = mapped_column(
        String(50), nullable=False, default=CaseStage.intake.value, index=True
    )
    outcome: Mapped[Optional[str]] = mapped_column(Text)
    fee_agreement_signed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    lead: Mapped[Optional[Lead]] = relationship("Lead", back_populates="cases")
    documents: Mapped[list[Document]] = relationship("Document", back_populates="case")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    template_version: Mapped[Optional[str]] = mapped_column(String(20))

    case: Mapped[Case] = relationship("Case", back_populates="documents")


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    county: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    leads_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    leads_new: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ScrapeRunStatus.failed.value
    )
    snapshot_path: Mapped[Optional[str]] = mapped_column(Text)
