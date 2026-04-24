"""Unit tests for document generator."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from proceeds_navigator.documents.generator import DocumentGenerator, DocumentContext


@pytest.fixture
def exports_dir(tmp_path):
    return tmp_path / "exports"


@pytest.fixture
def generator(exports_dir):
    return DocumentGenerator(exports_dir=exports_dir)


@pytest.fixture
def ctx():
    return DocumentContext(
        operator_name="Golden State Claimant Advisors",
        operator_address="123 Main St, Sacramento, CA 95814",
        operator_phone="555-555-5555",
        operator_email="info@gsca.example.com",
        client_name="Jane Doe",
        client_address="456 Oak Ave, Fresno, CA 93720",
        county_name="Fresno County",
        county_agency="Fresno County Tax Collector",
        parcel_apn="123-456-78",
        situs_address="789 Elm St, Fresno, CA 93720",
        sale_date="November 15, 2025",
        claim_deadline="November 15, 2026",
        case_number="GS-2025-0001",
        generated_date="April 24, 2026",
        direct_filing_note="Claimants may file directly with the Fresno County Tax Collector at no cost.",
    )


class TestDocumentGeneratorInit:
    def test_creates_exports_dir(self, exports_dir):
        DocumentGenerator(exports_dir=exports_dir)
        assert exports_dir.exists()

    def test_templates_dir_exists(self, generator):
        # Generator should find templates bundled with the package
        assert generator.templates_dir.exists()


class TestDocumentGeneration:
    @pytest.mark.parametrize("doc_type", [
        "outreach_intro",
        "outreach_followup",
        "intake_form",
        "document_checklist",
        "service_agreement",
        "claim_checklist",
        "case_summary",
    ])
    def test_generates_all_doc_types(self, generator, ctx, doc_type):
        output = generator.generate(doc_type=doc_type, context=ctx, case_number="GS-2025-0001")
        assert isinstance(output, str)
        assert len(output) > 100

    def test_output_contains_client_name(self, generator, ctx):
        output = generator.generate("outreach_intro", ctx, "GS-2025-0001")
        assert "Jane Doe" in output

    def test_output_contains_operator_name(self, generator, ctx):
        output = generator.generate("outreach_intro", ctx, "GS-2025-0001")
        assert "Golden State Claimant Advisors" in output

    def test_output_contains_county_name(self, generator, ctx):
        output = generator.generate("outreach_intro", ctx, "GS-2025-0001")
        assert "Fresno County" in output

    def test_output_contains_compliance_footer(self, generator, ctx):
        output = generator.generate("outreach_intro", ctx, "GS-2025-0001")
        # The compliance footer must state the operator is not a government agency
        assert "not a government agency" in output.lower() or "government agency" in output

    def test_compliance_footer_on_all_client_docs(self, generator, ctx):
        client_docs = [
            "outreach_intro",
            "outreach_followup",
            "intake_form",
            "service_agreement",
            "claim_checklist",
        ]
        for doc_type in client_docs:
            output = generator.generate(doc_type, ctx, "GS-2025-0001")
            assert "not a government agency" in output.lower(), (
                f"Compliance footer missing from {doc_type}"
            )

    def test_compliance_footer_includes_direct_filing_note(self, generator, ctx):
        output = generator.generate("outreach_intro", ctx, "GS-2025-0001")
        assert "no cost" in output.lower() or "at no cost" in output.lower()

    def test_service_agreement_has_legal_review_warning(self, generator, ctx):
        output = generator.generate("service_agreement", ctx, "GS-2025-0001")
        assert "legal review" in output.lower() or "attorney" in output.lower()

    def test_no_unfilled_placeholders(self, generator, ctx):
        for doc_type in [
            "outreach_intro", "outreach_followup", "intake_form",
            "document_checklist", "service_agreement", "claim_checklist", "case_summary"
        ]:
            output = generator.generate(doc_type, ctx, "GS-2025-0001")
            assert "{{" not in output, f"Unfilled placeholder in {doc_type}"
            assert "}}" not in output, f"Unfilled placeholder in {doc_type}"


class TestSaveToFile:
    def test_save_writes_file(self, generator, ctx, exports_dir):
        path = generator.save(
            doc_type="outreach_intro",
            context=ctx,
            case_number="GS-2025-0001",
        )
        assert path.exists()
        assert path.stat().st_size > 0

    def test_save_returns_path_inside_exports_dir(self, generator, ctx, exports_dir):
        path = generator.save("outreach_intro", ctx, "GS-2025-0001")
        assert str(path).startswith(str(exports_dir))

    def test_save_filename_includes_doc_type(self, generator, ctx):
        path = generator.save("intake_form", ctx, "GS-2025-0002")
        assert "intake_form" in path.name

    def test_save_filename_includes_case_number(self, generator, ctx):
        path = generator.save("intake_form", ctx, "GS-2025-0002")
        assert "GS-2025-0002" in path.name


class TestInvalidDocType:
    def test_invalid_doc_type_raises(self, generator, ctx):
        with pytest.raises((ValueError, KeyError)):
            generator.generate("nonexistent_template", ctx, "GS-2025-0001")
