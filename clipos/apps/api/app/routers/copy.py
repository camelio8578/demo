"""
Copy variant endpoints.

POST /api/v1/candidates/{id}/copy   — trigger copy generation for all platforms
GET  /api/v1/candidates/{id}/copy   — list copy variants
PUT  /api/v1/copy/{id}              — update copy variant (human edit)
"""
from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import CandidateClip, CopyVariant
from app.dependencies import get_db
from app.schemas.copy import (
    CopyGenerateRequest,
    CopyVariantListOut,
    CopyVariantOut,
    CopyVariantUpdate,
)

log = structlog.get_logger(__name__)

router = APIRouter(tags=["copy"])


@router.post(
    "/api/v1/candidates/{candidate_id}/copy",
    response_model=CopyVariantListOut,
    status_code=202,
)
def generate_copy(
    candidate_id: uuid.UUID,
    body: CopyGenerateRequest = CopyGenerateRequest(),
    db: Session = Depends(get_db),
) -> CopyVariantListOut:
    """
    Synchronously generate copy variants for the specified platforms.

    Uses rule-based generation by default (no LLM key required).
    Pass llm_provider="openai"|"anthropic" to use LLM if configured.
    """
    clip = db.query(CandidateClip).filter(CandidateClip.id == candidate_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Candidate clip not found")

    from workers.copy.copy_generator import CopyGenerator

    copy_gen = CopyGenerator()
    segment_text = clip.segment_text or ""
    created: list[CopyVariant] = []

    for platform in body.platforms:
        try:
            copy_data = copy_gen.generate_copy(
                segment_text=segment_text,
                platform=platform,
                creator_name="",
                llm_provider=body.llm_provider,
            )

            variant = CopyVariant(
                id=uuid.uuid4(),
                candidate_clip_id=clip.id,
                platform=platform,
                variant_index=0,
                hook=copy_data.get("hook"),
                title=copy_data.get("title"),
                caption=copy_data.get("caption"),
                hashtags=copy_data.get("hashtags", []),
                llm_model_used=copy_data.get("llm_model_used"),
                prompt_version=copy_data.get("prompt_version"),
            )
            db.add(variant)
            created.append(variant)
        except Exception as exc:
            log.warning(
                "copy_generation_failed",
                platform=platform,
                candidate_id=str(candidate_id),
                error=str(exc),
            )

    db.commit()
    for v in created:
        db.refresh(v)

    log.info(
        "copy_generated",
        candidate_id=str(candidate_id),
        platforms=body.platforms,
        created_count=len(created),
    )
    return CopyVariantListOut(items=created, total=len(created))


@router.get(
    "/api/v1/candidates/{candidate_id}/copy",
    response_model=CopyVariantListOut,
)
def list_copy_variants(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> CopyVariantListOut:
    """List all copy variants for a candidate clip."""
    clip = db.query(CandidateClip).filter(CandidateClip.id == candidate_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Candidate clip not found")

    variants = (
        db.query(CopyVariant)
        .filter(CopyVariant.candidate_clip_id == candidate_id)
        .order_by(CopyVariant.platform, CopyVariant.variant_index)
        .all()
    )
    return CopyVariantListOut(items=variants, total=len(variants))


@router.put("/api/v1/copy/{copy_id}", response_model=CopyVariantOut)
def update_copy_variant(
    copy_id: uuid.UUID,
    body: CopyVariantUpdate,
    db: Session = Depends(get_db),
) -> CopyVariant:
    """Apply human edits to a copy variant."""
    variant = db.query(CopyVariant).filter(CopyVariant.id == copy_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Copy variant not found")

    if body.hook is not None:
        variant.hook = body.hook
    if body.title is not None:
        variant.title = body.title
    if body.caption is not None:
        variant.caption = body.caption
    if body.hashtags is not None:
        variant.hashtags = body.hashtags

    db.commit()
    db.refresh(variant)

    log.info("copy_variant_updated", copy_id=str(copy_id))
    return variant
