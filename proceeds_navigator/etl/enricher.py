"""ETL enricher: adds derived fields to normalized lead dicts without external API calls."""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class Enricher:
    """Adds derived fields to a normalized lead dict using only the data itself."""

    def enrich(self, lead: dict[str, Any]) -> dict[str, Any]:
        """Return an enriched copy of *lead* with additional derived fields.

        Enrichment steps (all purely data-derived, no network calls):

        1. Infer ``claimant_source_basis`` when it is absent.
        2. Normalize APN format: strip surrounding whitespace, uppercase.
        """
        result = dict(lead)

        result = self._infer_claimant_source_basis(result)
        result = self._normalize_apn(result)

        logger.debug(
            "enricher.complete",
            county=result.get("county"),
            parcel_apn=result.get("parcel_apn"),
            claimant_source_basis=result.get("claimant_source_basis"),
        )
        return result

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _infer_claimant_source_basis(lead: dict[str, Any]) -> dict[str, Any]:
        """Set ``claimant_source_basis`` when it is not already present."""
        if lead.get("claimant_source_basis"):
            return lead

        claimant_type = lead.get("likely_claimant_type", "unknown")
        claimant_name = lead.get("likely_claimant_name")
        source_type = lead.get("source_type", "")

        if claimant_type == "former_owner" and claimant_name:
            lead["claimant_source_basis"] = (
                f"Former owner '{claimant_name}' identified via {source_type}"
            )
        elif claimant_type == "lienholder" and claimant_name:
            lead["claimant_source_basis"] = (
                f"Lienholder '{claimant_name}' identified via {source_type}"
            )
        elif claimant_name:
            lead["claimant_source_basis"] = (
                f"Claimant '{claimant_name}' identified via {source_type}"
            )
        else:
            lead["claimant_source_basis"] = None

        return lead

    @staticmethod
    def _normalize_apn(lead: dict[str, Any]) -> dict[str, Any]:
        """Strip surrounding whitespace and uppercase the parcel APN."""
        apn = lead.get("parcel_apn")
        if apn is not None:
            lead["parcel_apn"] = str(apn).strip().upper()
        return lead
