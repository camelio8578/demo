"""Document generator using Jinja2 templates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

log = structlog.get_logger()

TEMPLATE_VERSION = "1.0.0"

VALID_DOC_TYPES = {
    "outreach_intro",
    "outreach_followup",
    "intake_form",
    "document_checklist",
    "service_agreement",
    "claim_checklist",
    "case_summary",
}


@dataclass
class DocumentContext:
    operator_name: str
    operator_address: str
    operator_phone: str
    operator_email: str
    client_name: str
    client_address: str
    county_name: str
    county_agency: str
    parcel_apn: str
    situs_address: str
    sale_date: str
    claim_deadline: str
    case_number: str
    generated_date: str
    direct_filing_note: str
    operator_website: str = ""
    client_contact: str = ""
    notes: str = ""


class DocumentGenerator:
    def __init__(self, exports_dir: Optional[Path] = None):
        self.templates_dir = Path(__file__).parent / "templates"
        self.exports_dir = Path(exports_dir) if exports_dir else Path("./data/exports")
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.template_version = TEMPLATE_VERSION
        self._env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            undefined=StrictUndefined,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self, doc_type: str, context: DocumentContext, case_number: str) -> str:
        """Render template to string. Raises ValueError for unknown doc_type."""
        if doc_type not in VALID_DOC_TYPES:
            raise ValueError(f"Unknown doc_type '{doc_type}'. Valid: {VALID_DOC_TYPES}")
        template_name = f"{doc_type}.txt.j2"
        try:
            template = self._env.get_template(template_name)
        except TemplateNotFound as exc:
            raise ValueError(f"Template file not found: {template_name}") from exc
        rendered = template.render(**context.__dict__, template_version=TEMPLATE_VERSION)
        return rendered

    def save(self, doc_type: str, context: DocumentContext, case_number: str) -> Path:
        """Render and save to exports_dir. Returns file path."""
        content = self.generate(doc_type, context, case_number)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_case = case_number.replace("/", "-")
        filename = f"{safe_case}_{doc_type}_{ts}.txt"
        path = self.exports_dir / filename
        path.write_text(content, encoding="utf-8")
        log.info("document_saved", doc_type=doc_type, case_number=case_number, path=str(path))
        return path
