"""Shared pytest fixtures for Proceeds Navigator tests."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Point at in-memory SQLite for all tests
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())
os.environ.setdefault("LOG_LEVEL", "warning")
os.environ.setdefault("OPERATOR_NAME", "Test Operator")
os.environ.setdefault("OPERATOR_ADDRESS", "123 Test St, Sacramento, CA 95814")
os.environ.setdefault("OPERATOR_PHONE", "555-555-5555")
os.environ.setdefault("OPERATOR_EMAIL", "test@example.com")
os.environ.setdefault("LEGAL_REVIEW_AMOUNT_THRESHOLD", "50000")


from proceeds_navigator.db.models import Base  # noqa: E402


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Session:
    """Fresh session wrapping a transaction that is rolled back after each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sample_raw_lead() -> dict:
    """Minimal raw dict as produced by a county scraper."""
    return {
        "county": "fresno",
        "source_type": "auction_list",
        "source_url": "https://www.fresnocounty.gov/tax-collector/test",
        "page_title": "Tax Sale Results — Fresno County",
        "parcel_apn": "123-456-78",
        "situs_address": "1234 Main St, Fresno, CA 93720",
        "sale_date_raw": "2025-11-15",
        "notice_date_raw": "2025-10-01",
        "excess_proceeds_signal": "Excess proceeds: $12,500.00",
        "likely_claimant_name": "John Smith",
    }


@pytest.fixture
def sample_lead_dict() -> dict:
    """Normalized lead dict matching Lead model fields."""
    return {
        "county": "fresno",
        "source_type": "auction_list",
        "source_url": "https://www.fresnocounty.gov/tax-collector/test",
        "page_title": "Tax Sale Results",
        "parcel_apn": "123-456-78",
        "situs_address": "1234 Main St, Fresno, CA 93720",
        "excess_proceeds_signal": "Excess proceeds: $12,500.00",
        "excess_proceeds_amount": 12500.0,
        "likely_claimant_type": "former_owner",
        "likely_claimant_name": "John Smith",
        "claimant_source_basis": "Named in auction source",
    }


SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"
