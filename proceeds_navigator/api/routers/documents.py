"""Document generation endpoints."""

from __future__ import annotations

import os
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from proceeds_navigator.api.deps import get_db
from proceeds_navigator.api.schemas import DocumentRecord, DocumentRequest
from proceeds_navigator.db.models import Case, Document
from proceeds_navigator.documents.generator import DocumentContext, DocumentGenerator

log = structlog.get_logger()
router = APIRouter(tags=["documents"])

# LEGAL_REVIEW_REQUIRED: service_agreement template must not be sent without attorney review
_LEGAL_REVIEW_DOCS = {"service_agreement"}


def _get_generator() -> DocumentGenerator:
    exports_dir = Path(os.getenv("EXPORTS_DIR", "./data/exports"))
    return DocumentGenerator(exports_dir=exports_dir)


def _build_context(case: Case) -> DocumentContext:
    county_names = {
        "fresno": "Fresno County",
        "san_diego": "San Diego County",
        "sacramento": "Sacramento County",
        "los_angeles": "Los Angeles County",
    }
    agency_names = {
        "fresno": "Fresno County Tax Collector",
        "san_diego": "San Diego County Treasurer-Tax Collector",
        "sacramento": "Sacramento County Tax Collector",
        "los_angeles": "Los Angeles County Treasurer and Tax Collector",
    }
    direct_filing_notes = {
        "fresno": "Claimants may file directly with the Fresno County Tax Collector at no cost.",
        "san_diego": "Claimants may file directly with the San Diego County Treasurer-Tax Collector at no cost.",
        "sacramento": "Claimants may file directly with the Sacramento County Tax Collector at no cost.",
        "los_angeles": "Claimants may file directly with the Los Angeles County Treasurer and Tax Collector at no cost.",
    }
    county_key = case.county
    return DocumentContext(
        operator_name=os.getenv("OPERATOR_NAME", "Golden State Claimant Advisors"),
        operator_address=os.getenv("OPERATOR_ADDRESS", ""),
        operator_phone=os.getenv("OPERATOR_PHONE", ""),
        operator_email=os.getenv("OPERATOR_EMAIL", ""),
        client_name=case.client_name or "[CLIENT NAME]",
        client_address="[CLIENT ADDRESS — complete in document]",
        county_name=county_names.get(county_key, county_key),
        county_agency=agency_names.get(county_key, "County Tax Collector"),
        parcel_apn=case.parcel_apn or "[APN]",
        situs_address="[PROPERTY ADDRESS — verify from lead]",
        sale_date=str(case.lead.sale_date) if case.lead and case.lead.sale_date else "[SALE DATE]",
        claim_deadline=str(case.claim_deadline) if case.claim_deadline else "[DEADLINE — verify]",
        case_number=case.case_number,
        generated_date=__import__("datetime").date.today().strftime("%B %d, %Y"),
        direct_filing_note=direct_filing_notes.get(
            county_key,
            "Claimants may file directly with the county at no cost.",
        ),
    )


@router.get("/cases/{case_id}/documents", response_model=list[DocumentRecord])
def list_documents(case_id: int, db: Session = Depends(get_db)) -> list[DocumentRecord]:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return [DocumentRecord.model_validate(d) for d in case.documents]


@router.post("/cases/{case_id}/documents", response_model=DocumentRecord, status_code=201)
def generate_document(
    case_id: int,
    request: DocumentRequest,
    db: Session = Depends(get_db),
) -> DocumentRecord:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if request.doc_type in _LEGAL_REVIEW_DOCS:
        log.warning(
            "legal_review_doc_generated",
            doc_type=request.doc_type,
            case_id=case_id,
            # LEGAL_REVIEW_REQUIRED: this document is a draft only
        )

    generator = _get_generator()
    ctx = _build_context(case)
    try:
        file_path = generator.save(
            doc_type=request.doc_type,
            context=ctx,
            case_number=case.case_number,
        )
    except Exception as exc:
        log.error("document_generation_failed", case_id=case_id, doc_type=request.doc_type, error=str(exc))
        raise HTTPException(status_code=500, detail=f"Document generation failed: {exc}")

    doc = Document(
        case_id=case_id,
        doc_type=request.doc_type,
        file_path=str(file_path),
        template_version=generator.template_version,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    log.info("document_generated", case_id=case_id, doc_type=request.doc_type, path=str(file_path))
    return DocumentRecord.model_validate(doc)


@router.get("/documents/{doc_id}/download")
def download_document(doc_id: int, db: Session = Depends(get_db)) -> FileResponse:
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.file_path or not Path(doc.file_path).exists():
        raise HTTPException(status_code=404, detail="Document file not found on disk")
    return FileResponse(
        path=doc.file_path,
        filename=Path(doc.file_path).name,
        media_type="text/plain",
    )
