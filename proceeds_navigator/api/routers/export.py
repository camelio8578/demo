"""CSV export endpoints."""

from __future__ import annotations

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from proceeds_navigator.api.deps import get_db
from proceeds_navigator.db.models import Case, Lead

router = APIRouter(prefix="/export", tags=["export"])

LEAD_FIELDS = [
    "id", "county", "source_type", "source_url", "page_title",
    "parcel_apn", "situs_address", "sale_date", "notice_date",
    "board_item_id", "excess_proceeds_signal", "excess_proceeds_amount",
    "likely_claimant_type", "likely_claimant_name", "claimant_source_basis",
    "priority_rank", "score", "legal_risk_flag",
    "review_status", "outreach_status", "notes",
    "last_checked_at", "content_hash", "created_at",
]

CASE_FIELDS = [
    "id", "case_number", "lead_id", "client_name", "client_contact",
    "county", "parcel_apn", "claim_deadline", "stage", "outcome",
    "fee_agreement_signed", "notes", "created_at",
]


def _stream_csv(headers: list[str], rows: list[dict]) -> StreamingResponse:
    def generate():
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore", lineterminator="\r\n")
        writer.writeheader()
        yield buf.getvalue()
        for row in rows:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore", lineterminator="\r\n")
            writer.writerow({k: (str(v) if v is not None else "") for k, v in row.items()})
            yield buf.getvalue()

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=leads_{ts}.csv"},
    )


@router.get("/leads.csv")
def export_leads(db: Session = Depends(get_db)) -> StreamingResponse:
    leads = db.scalars(select(Lead).order_by(Lead.priority_rank.asc(), Lead.score.desc())).all()
    rows = [{f: getattr(lead, f, None) for f in LEAD_FIELDS} for lead in leads]
    return _stream_csv(LEAD_FIELDS, rows)


@router.get("/cases.csv")
def export_cases(db: Session = Depends(get_db)) -> StreamingResponse:
    cases = db.scalars(select(Case).order_by(Case.claim_deadline.asc())).all()
    rows = [{f: getattr(case, f, None) for f in CASE_FIELDS} for case in cases]
    resp = _stream_csv(CASE_FIELDS, rows)
    # Fix filename for cases
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    resp.headers["Content-Disposition"] = f"attachment; filename=cases_{ts}.csv"
    return resp
