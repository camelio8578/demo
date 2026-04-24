"""ETL deduplicator: stable SHA-256 hashing and duplicate filtering for leads."""

from __future__ import annotations

import hashlib
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Fields that constitute a lead's identity for deduplication purposes.
_HASH_FIELDS = ("county", "parcel_apn", "sale_date", "source_url")


class Deduplicator:
    """Detects and removes duplicate leads using a content-addressable hash."""

    # ── Public API ────────────────────────────────────────────────────────────

    def compute_hash(self, lead: dict[str, Any]) -> str:
        """Return a stable 64-character SHA-256 hex digest for *lead*.

        Only the identity fields (county, parcel_apn, sale_date, source_url)
        are included.  Missing or None fields are treated as empty strings so
        the hash is always computable.
        """
        parts = [str(lead.get(field) or "") for field in _HASH_FIELDS]
        raw = "|".join(parts).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def is_duplicate(self, lead: dict[str, Any], existing_hashes: set[str]) -> bool:
        """Return True if *lead* has already been seen (hash in *existing_hashes*)."""
        return self.compute_hash(lead) in existing_hashes

    def filter_new(
        self, leads: list[dict[str, Any]], existing_hashes: set[str]
    ) -> list[dict[str, Any]]:
        """Return only the leads that are genuinely new.

        Removes leads whose hash appears in *existing_hashes* and also
        deduplicates within the batch itself (first occurrence of each hash
        wins).
        """
        seen: set[str] = set(existing_hashes)
        new_leads: list[dict[str, Any]] = []
        for lead in leads:
            h = self.compute_hash(lead)
            if h not in seen:
                seen.add(h)
                new_leads.append(lead)
            else:
                logger.debug(
                    "deduplicator.skipped",
                    county=lead.get("county"),
                    parcel_apn=lead.get("parcel_apn"),
                    content_hash=h,
                )
        logger.info(
            "deduplicator.filter_complete",
            total=len(leads),
            kept=len(new_leads),
            dropped=len(leads) - len(new_leads),
        )
        return new_leads
