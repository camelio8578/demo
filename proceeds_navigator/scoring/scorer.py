"""Lead scoring engine for Proceeds Navigator."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Points ceiling for each dimension
_MAX_SOURCE_RELIABILITY = 20
_MAX_PROCEEDS_EXISTENCE = 25
_MAX_CLAIMANT_TRACEABILITY = 20
_MAX_DOCUMENT_COMPLEXITY = 10
_MAX_DEADLINE_URGENCY = 15

# Deadline thresholds (days elapsed since sale)
_DEADLINE_MEDIUM_THRESHOLD = 180   # 180–274 days elapsed  → medium urgency (10 pts)
_DEADLINE_HIGH_THRESHOLD = 275     # ≥275 days elapsed     → high urgency  (15 pts)


def _legal_review_threshold() -> float:
    """Read LEGAL_REVIEW_AMOUNT_THRESHOLD from env, default 50 000."""
    try:
        return float(os.environ.get("LEGAL_REVIEW_AMOUNT_THRESHOLD", "50000"))
    except (ValueError, TypeError):
        return 50_000.0


@dataclass
class ScoreResult:
    score: float                              # 0.0 – 100.0
    priority_rank: int                        # 1 – 5
    legal_risk_flag: str                      # low | medium | high | REQUIRES_LEGAL_REVIEW
    explanation: dict[str, dict[str, Any]] = field(default_factory=dict)


class LeadScorer:
    """Score a normalized lead dict and return a :class:`ScoreResult`."""

    def score(self, lead: dict[str, Any]) -> ScoreResult:
        explanation: dict[str, dict[str, Any]] = {}

        # ── Dimension scores ──────────────────────────────────────────────────
        src_pts, src_reason = self._score_source_reliability(lead)
        explanation["source_reliability"] = {"points": src_pts, "reason": src_reason}

        proc_pts, proc_reason = self._score_proceeds_existence(lead)
        explanation["proceeds_existence"] = {"points": proc_pts, "reason": proc_reason}

        claim_pts, claim_reason = self._score_claimant_traceability(lead)
        explanation["claimant_traceability"] = {"points": claim_pts, "reason": claim_reason}

        doc_pts, doc_reason = self._score_document_complexity(lead)
        explanation["document_complexity"] = {"points": doc_pts, "reason": doc_reason}

        deadline_pts, deadline_reason = self._score_deadline_urgency(lead)
        explanation["deadline_urgency"] = {"points": deadline_pts, "reason": deadline_reason}

        raw_score = float(src_pts + proc_pts + claim_pts + doc_pts + deadline_pts)

        # ── Penalties ─────────────────────────────────────────────────────────
        penalty = 0
        if not lead.get("parcel_apn"):
            penalty += 5
            explanation["penalty_missing_apn"] = {
                "points": -5,
                "reason": "Parcel APN is absent; property cannot be uniquely identified",
            }

        claimant_type = lead.get("likely_claimant_type", "unknown")
        claimant_name = lead.get("likely_claimant_name")
        if claimant_type == "unknown" and claimant_name is None:
            penalty += 5
            explanation["penalty_unknown_entity"] = {
                "points": -5,
                "reason": "Claimant type is unknown and no claimant name is recorded",
            }

        final_score = max(0.0, raw_score - penalty)

        # ── Legal risk flag ───────────────────────────────────────────────────
        legal_risk_flag = self._determine_legal_risk(lead, final_score, claimant_type)

        # ── Priority rank ─────────────────────────────────────────────────────
        priority_rank = self._determine_priority_rank(final_score)

        logger.debug(
            "scorer.complete",
            county=lead.get("county"),
            parcel_apn=lead.get("parcel_apn"),
            score=final_score,
            priority_rank=priority_rank,
            legal_risk_flag=legal_risk_flag,
        )

        return ScoreResult(
            score=final_score,
            priority_rank=priority_rank,
            legal_risk_flag=legal_risk_flag,
            explanation=explanation,
        )

    # ── Dimension scorers ─────────────────────────────────────────────────────

    @staticmethod
    def _score_source_reliability(lead: dict[str, Any]) -> tuple[int, str]:
        source_type = lead.get("source_type", "")
        if source_type == "auction_list":
            return 20, "Primary auction list — highest confidence source"
        if source_type == "agenda_item":
            return 15, "Board agenda item — official government document"
        if source_type == "press_release":
            return 10, "Press release — moderately reliable secondary source"
        if source_type in ("web_page", "notice"):
            return 5, f"Source type '{source_type}' — indirect or unverified source"
        return 3, f"Source type '{source_type}' — low-confidence source"

    @staticmethod
    def _score_proceeds_existence(lead: dict[str, Any]) -> tuple[int, str]:
        amount = lead.get("excess_proceeds_amount")
        if amount is not None:
            return 25, f"Stated excess proceeds amount: ${amount:,.2f}"
        signal = lead.get("excess_proceeds_signal") or ""
        if "excess proceeds" in signal.lower():
            return 8, "Signal text mentions excess proceeds but no dollar amount extracted"
        return 3, "No explicit excess proceeds signal found"

    @staticmethod
    def _score_claimant_traceability(lead: dict[str, Any]) -> tuple[int, str]:
        claimant_type = lead.get("likely_claimant_type", "unknown")
        claimant_name = lead.get("likely_claimant_name")

        if claimant_type == "former_owner" and claimant_name is not None:
            return 20, f"Named former owner: {claimant_name}"
        if claimant_type == "lienholder":
            return 15, "Lienholder identified — traceable but legally complex"
        if claimant_name is not None:
            return 10, f"Partial claimant identification: {claimant_name}"
        return 5, "No claimant identified"

    @staticmethod
    def _score_document_complexity(lead: dict[str, Any]) -> tuple[int, str]:
        claimant_type = lead.get("likely_claimant_type", "unknown")
        signal = (lead.get("excess_proceeds_signal") or "").lower()

        if claimant_type == "lienholder":
            return 3, "Lienholder involved — title/lien documents required; high complexity"
        if "lien" in signal:
            return 6, "Lien reference detected in signal — moderate document complexity"
        return 10, "No lien signals detected; straightforward single-owner scenario"

    @staticmethod
    def _score_deadline_urgency(lead: dict[str, Any]) -> tuple[int, str]:
        sale_date = lead.get("sale_date")
        if sale_date is None:
            return 0, "Sale date unknown — deadline urgency cannot be assessed"

        # sale_date may arrive as a date object or an ISO string
        if isinstance(sale_date, str):
            from dateutil import parser as _dp
            try:
                sale_date = _dp.parse(sale_date).date()
            except Exception:
                return 0, "Sale date could not be parsed — urgency unknown"

        days_elapsed = (date.today() - sale_date).days

        if days_elapsed >= _DEADLINE_HIGH_THRESHOLD:
            return 15, (
                f"{days_elapsed} days since sale — fewer than 3 months to the "
                "1-year deadline; critical urgency"
            )
        if days_elapsed >= _DEADLINE_MEDIUM_THRESHOLD:
            return 10, (
                f"{days_elapsed} days since sale — 3–6 months to the 1-year "
                "deadline; elevated urgency"
            )
        return 5, (
            f"{days_elapsed} days since sale — more than 6 months to the "
            "1-year deadline; low urgency"
        )

    # ── Risk and rank helpers ─────────────────────────────────────────────────

    @staticmethod
    def _determine_legal_risk(
        lead: dict[str, Any], score: float, claimant_type: str
    ) -> str:
        amount = lead.get("excess_proceeds_amount")
        threshold = _legal_review_threshold()

        # Mandatory escalation triggers
        if claimant_type == "lienholder":
            return "REQUIRES_LEGAL_REVIEW"
        if amount is not None and amount >= threshold:
            return "REQUIRES_LEGAL_REVIEW"

        # Score-based risk
        claimant_name = lead.get("likely_claimant_name")
        claimant_not_identified = claimant_type == "unknown" and claimant_name is None
        if score <= 40 and claimant_not_identified:
            return "high"

        # Structural risk indicators
        parcel_apn = lead.get("parcel_apn")
        source_type = lead.get("source_type", "")
        indirect_source = source_type in ("web_page", "notice", "press_release")
        if parcel_apn is None or indirect_source:
            return "medium"

        return "low"

    @staticmethod
    def _determine_priority_rank(score: float) -> int:
        if score >= 80:
            return 1
        if score >= 60:
            return 2
        if score >= 40:
            return 3
        if score >= 20:
            return 4
        return 5
