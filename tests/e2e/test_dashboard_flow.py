"""End-to-end API flow test: lead → qualify → case → document."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from proceeds_navigator.api.main import create_app
from proceeds_navigator.api.deps import get_db
from proceeds_navigator.db.models import Base, Lead
from proceeds_navigator.scoring.scorer import LeadScorer
from proceeds_navigator.scoring.explainer import explanation_to_json


@pytest.fixture(scope="module")
def engine():
    # StaticPool ensures all sessions share the same physical SQLite connection,
    # preventing separate in-memory databases from being created per connection.
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture(scope="module")
def session_factory(engine):
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="module")
def client(engine, session_factory, tmp_path_factory):
    import os
    exports = tmp_path_factory.mktemp("exports")
    os.environ["EXPORTS_DIR"] = str(exports)
    os.environ["OPERATOR_NAME"] = "Golden State Claimant Advisors"
    os.environ["OPERATOR_ADDRESS"] = "123 Test St, Sacramento, CA 95814"
    os.environ["OPERATOR_PHONE"] = "555-555-5555"
    os.environ["OPERATOR_EMAIL"] = "test@example.com"

    app = create_app()

    def override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def seeded_lead_id(engine, session_factory):
    """Insert a test lead and return its ID."""
    scorer = LeadScorer()
    lead_dict = {
        "county": "fresno",
        "source_type": "auction_list",
        "excess_proceeds_amount": 12500.0,
        "likely_claimant_type": "former_owner",
        "likely_claimant_name": "Test Owner",
        "parcel_apn": "E2E-001-01",
        "sale_date": date.today() - timedelta(days=30),
    }
    score_result = scorer.score(lead_dict)
    session = session_factory()
    try:
        lead = Lead(
            county="fresno",
            source_type="auction_list",
            source_url="https://test.example.com/e2e",
            parcel_apn="E2E-001-01",
            situs_address="1 E2E Ave, Fresno, CA 93720",
            excess_proceeds_amount=12500.0,
            excess_proceeds_signal="Excess proceeds: $12,500.00",
            likely_claimant_type="former_owner",
            likely_claimant_name="Test Owner",
            sale_date=date.today() - timedelta(days=30),
            score=score_result.score,
            priority_rank=score_result.priority_rank,
            legal_risk_flag=score_result.legal_risk_flag,
            score_explanation=explanation_to_json(score_result.explanation),
            review_status="pending",
            outreach_status="none",
            content_hash="e2e_test_hash_001",
        )
        session.add(lead)
        session.commit()
        session.refresh(lead)
        return lead.id
    finally:
        session.close()


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "lead_count" in data


class TestLeadEndpoints:
    def test_list_leads_returns_200(self, client, seeded_lead_id):
        resp = client.get("/api/v1/leads")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_get_lead_detail(self, client, seeded_lead_id):
        resp = client.get(f"/api/v1/leads/{seeded_lead_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == seeded_lead_id
        assert data["county"] == "fresno"
        assert data["parcel_apn"] == "E2E-001-01"

    def test_lead_detail_has_score_explanation(self, client, seeded_lead_id):
        resp = client.get(f"/api/v1/leads/{seeded_lead_id}")
        data = resp.json()
        assert data["score_explanation"] is not None
        assert "source_reliability" in data["score_explanation"]

    def test_get_lead_404(self, client):
        resp = client.get("/api/v1/leads/999999")
        assert resp.status_code == 404

    def test_filter_by_county(self, client, seeded_lead_id):
        resp = client.get("/api/v1/leads?county=fresno")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["county"] == "fresno"

    def test_rescore_lead(self, client, seeded_lead_id):
        resp = client.get(f"/api/v1/leads/{seeded_lead_id}/score")
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] is not None
        assert 0 <= data["score"] <= 100


class TestLeadQualifyFlow:
    def test_update_status_to_reviewed(self, client, seeded_lead_id):
        resp = client.patch(
            f"/api/v1/leads/{seeded_lead_id}/status",
            json={"review_status": "reviewed"},
        )
        assert resp.status_code == 200
        assert resp.json()["review_status"] == "reviewed"

    def test_update_status_to_qualified(self, client, seeded_lead_id):
        resp = client.patch(
            f"/api/v1/leads/{seeded_lead_id}/status",
            json={"review_status": "qualified"},
        )
        assert resp.status_code == 200
        assert resp.json()["review_status"] == "qualified"

    def test_invalid_status_returns_422(self, client, seeded_lead_id):
        resp = client.patch(
            f"/api/v1/leads/{seeded_lead_id}/status",
            json={"review_status": "INVALID_STATUS"},
        )
        assert resp.status_code == 422


class TestCaseFlow:
    def test_create_case_from_qualified_lead(self, client, seeded_lead_id):
        resp = client.post(
            "/api/v1/cases",
            json={
                "lead_id": seeded_lead_id,
                "client_name": "Test Owner",
                "client_contact": "555-111-2222",
                "claim_deadline": str(date.today() + timedelta(days=200)),
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["case_number"].startswith("GS-")
        assert data["stage"] == "intake"
        assert data["county"] == "fresno"

    def test_cannot_create_case_from_unqualified_lead(self, client, engine, session_factory):
        session = session_factory()
        try:
            lead = Lead(
                county="san_diego",
                source_type="web_page",
                review_status="pending",
                likely_claimant_type="unknown",
                content_hash="unqualified_test_hash_002",
            )
            session.add(lead)
            session.commit()
            session.refresh(lead)
            unqualified_id = lead.id
        finally:
            session.close()

        resp = client.post("/api/v1/cases", json={"lead_id": unqualified_id})
        assert resp.status_code == 422

    def test_list_cases(self, client):
        resp = client.get("/api/v1/cases")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_update_case_stage(self, client, seeded_lead_id):
        cases_resp = client.get("/api/v1/cases")
        cases = cases_resp.json()["items"]
        if not cases:
            pytest.skip("No cases to update")
        case_id = cases[0]["id"]
        resp = client.patch(f"/api/v1/cases/{case_id}", json={"stage": "docs_gathering"})
        assert resp.status_code == 200
        assert resp.json()["stage"] == "docs_gathering"


class TestDocumentFlow:
    def test_generate_outreach_intro(self, client):
        cases_resp = client.get("/api/v1/cases")
        cases = cases_resp.json()["items"]
        if not cases:
            pytest.skip("No cases available")
        case_id = cases[0]["id"]

        resp = client.post(
            f"/api/v1/cases/{case_id}/documents",
            json={"doc_type": "outreach_intro"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["doc_type"] == "outreach_intro"
        assert data["file_path"] is not None

    def test_list_documents_for_case(self, client):
        cases_resp = client.get("/api/v1/cases")
        cases = cases_resp.json()["items"]
        if not cases:
            pytest.skip("No cases available")
        case_id = cases[0]["id"]

        resp = client.get(f"/api/v1/cases/{case_id}/documents")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_invalid_doc_type_returns_422(self, client):
        cases_resp = client.get("/api/v1/cases")
        cases = cases_resp.json()["items"]
        if not cases:
            pytest.skip("No cases available")
        case_id = cases[0]["id"]

        resp = client.post(
            f"/api/v1/cases/{case_id}/documents",
            json={"doc_type": "nonexistent_type"},
        )
        assert resp.status_code == 422


class TestExportEndpoints:
    def test_leads_csv_returns_200(self, client, seeded_lead_id):
        resp = client.get("/api/v1/export/leads.csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert len(resp.content) > 0

    def test_cases_csv_returns_200(self, client):
        resp = client.get("/api/v1/export/cases.csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    def test_leads_csv_has_header(self, client, seeded_lead_id):
        resp = client.get("/api/v1/export/leads.csv")
        first_line = resp.text.split("\r\n")[0]
        assert "county" in first_line
        assert "parcel_apn" in first_line
