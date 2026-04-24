"""ETL normalizer: converts raw scraper output dicts to clean Lead-ready dicts."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

import structlog
from dateutil import parser as dateutil_parser
from dateutil.parser import ParserError as DateutilParserError

logger = structlog.get_logger(__name__)

# Regex that matches an optional leading $ then a numeric amount.
# Alternatives are ordered longest-match-first:
#   1. Comma-grouped thousands with mandatory decimal  e.g. $12,500.00
#   2. Comma-grouped thousands without decimal         e.g. $12,500
#   3. Plain decimal float (no commas)                 e.g. 8750.50
#   4. Plain integer                                   e.g. 8750
_AMOUNT_RE = re.compile(
    r"\$?"
    r"("
    r"\d{1,3}(?:,\d{3})+\.\d+"   # comma-grouped + decimal  e.g. 12,500.00
    r"|"
    r"\d{1,3}(?:,\d{3})+"        # comma-grouped, no decimal e.g. 12,500
    r"|"
    r"\d+\.\d+"                  # plain decimal             e.g. 8750.50
    r"|"
    r"\d+"                       # plain integer             e.g. 8750
    r")"
)


class ParseError(ValueError):
    """Raised when a raw scraper dict cannot be normalized into a valid Lead."""


class Normalizer:
    VALID_COUNTIES = {"fresno", "san_diego", "sacramento", "los_angeles"}

    # ── Public API ────────────────────────────────────────────────────────────

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Convert a raw scraper output dict to a clean, Lead-ready dict.

        Raises:
            ParseError: if required fields are missing or values are invalid.
        """
        log = logger.bind(raw_keys=list(raw.keys()))
        result: dict[str, Any] = {}

        # 1. Strip whitespace from every string field first so validation
        #    operates on the cleaned values.
        stripped = self._strip_strings(raw)

        # 2. Validate and copy county.
        result["county"] = self._validate_county(stripped)

        # 3. Validate and copy source_type.
        result["source_type"] = self._validate_source_type(stripped)

        # 4. Pass through optional string fields verbatim (already stripped).
        for field in ("source_url", "page_title", "situs_address", "board_item_id",
                      "excess_proceeds_signal", "likely_claimant_name",
                      "claimant_source_basis"):
            if field in stripped:
                result[field] = stripped[field] if stripped[field] != "" else None
            else:
                result[field] = None

        # 5. Parcel APN — strip and return None if absent.
        result["parcel_apn"] = self._parse_apn(stripped)

        # 6. Date fields.
        result["sale_date"] = self._parse_date(stripped.get("sale_date_raw"))
        result["notice_date"] = self._parse_date(stripped.get("notice_date_raw"))

        # 7. Excess proceeds amount extracted from signal string.
        result["excess_proceeds_amount"] = self._parse_amount(
            stripped.get("excess_proceeds_signal")
        )

        # 8. Claimant type inference.
        result["likely_claimant_type"] = self._resolve_claimant_type(stripped, result)

        log.debug(
            "normalizer.complete",
            county=result["county"],
            parcel_apn=result["parcel_apn"],
            sale_date=str(result["sale_date"]),
        )
        return result

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _strip_strings(raw: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of raw with all string values whitespace-stripped."""
        return {k: (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}

    def _validate_county(self, stripped: dict[str, Any]) -> str:
        raw_county = stripped.get("county")
        if not raw_county:
            raise ParseError("county is required but was missing or empty")
        if raw_county not in self.VALID_COUNTIES:
            raise ParseError(
                f"county '{raw_county}' is not one of the supported counties: "
                f"{sorted(self.VALID_COUNTIES)}"
            )
        return raw_county

    @staticmethod
    def _validate_source_type(stripped: dict[str, Any]) -> str:
        source_type = stripped.get("source_type")
        if not source_type:
            raise ParseError("source_type is required but was missing or empty")
        return source_type

    @staticmethod
    def _parse_apn(stripped: dict[str, Any]) -> str | None:
        apn = stripped.get("parcel_apn")
        if apn is None or apn == "":
            return None
        return apn  # already stripped by _strip_strings

    @staticmethod
    def _parse_date(raw_value: str | None) -> date | None:
        if not raw_value:
            return None
        try:
            parsed = dateutil_parser.parse(raw_value, dayfirst=False)
            return parsed.date()
        except (DateutilParserError, ValueError, OverflowError):
            logger.debug("normalizer.date_parse_failed", raw_value=raw_value)
            return None

    @staticmethod
    def _parse_amount(signal: str | None) -> float | None:
        """Extract the first dollar amount from the signal string.

        Recognises patterns like ``$12,500.00`` and bare ``8750.50``.
        Returns None when no numeric amount is found.
        """
        if not signal:
            return None
        match = _AMOUNT_RE.search(signal)
        if not match:
            return None
        # Remove thousands commas before converting.
        numeric_str = match.group(1).replace(",", "")
        try:
            return float(numeric_str)
        except ValueError:
            return None

    @staticmethod
    def _resolve_claimant_type(
        stripped: dict[str, Any], result: dict[str, Any]
    ) -> str:
        """Determine the likely_claimant_type value with inference rules."""
        explicit = stripped.get("likely_claimant_type")
        if explicit:
            return explicit
        # Infer "former_owner" when a name is present but type was not set.
        claimant_name = result.get("likely_claimant_name")
        if claimant_name:
            return "former_owner"
        return "unknown"
