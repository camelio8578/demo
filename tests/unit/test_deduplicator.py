"""Unit tests for deduplicator."""

from __future__ import annotations

import pytest

from proceeds_navigator.etl.deduplicator import Deduplicator


@pytest.fixture
def deduper():
    return Deduplicator()


@pytest.fixture
def lead_a():
    return {
        "county": "fresno",
        "parcel_apn": "123-456-78",
        "sale_date": "2025-11-15",
        "source_url": "https://www.fresnocounty.gov/test",
    }


@pytest.fixture
def lead_b():
    return {
        "county": "san_diego",
        "parcel_apn": "999-001-01",
        "sale_date": "2025-12-01",
        "source_url": "https://www.sdttc.com/test",
    }


class TestHashGeneration:
    def test_produces_64_char_hex(self, deduper, lead_a):
        h = deduper.compute_hash(lead_a)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_input_same_hash(self, deduper, lead_a):
        assert deduper.compute_hash(lead_a) == deduper.compute_hash(lead_a)

    def test_different_county_different_hash(self, deduper, lead_a, lead_b):
        assert deduper.compute_hash(lead_a) != deduper.compute_hash(lead_b)

    def test_different_apn_different_hash(self, deduper, lead_a):
        lead_a_copy = {**lead_a, "parcel_apn": "999-999-99"}
        assert deduper.compute_hash(lead_a) != deduper.compute_hash(lead_a_copy)

    def test_different_sale_date_different_hash(self, deduper, lead_a):
        lead_a_copy = {**lead_a, "sale_date": "2025-12-01"}
        assert deduper.compute_hash(lead_a) != deduper.compute_hash(lead_a_copy)

    def test_hash_ignores_score_field(self, deduper, lead_a):
        lead_with_score = {**lead_a, "score": 85.0}
        assert deduper.compute_hash(lead_a) == deduper.compute_hash(lead_with_score)

    def test_hash_ignores_notes_field(self, deduper, lead_a):
        lead_with_notes = {**lead_a, "notes": "some note"}
        assert deduper.compute_hash(lead_a) == deduper.compute_hash(lead_with_notes)

    def test_none_apn_produces_stable_hash(self, deduper):
        lead = {"county": "fresno", "parcel_apn": None, "sale_date": "2025-11-15", "source_url": "https://x.com"}
        h1 = deduper.compute_hash(lead)
        h2 = deduper.compute_hash(lead)
        assert h1 == h2

    def test_missing_field_produces_stable_hash(self, deduper):
        lead = {"county": "fresno"}
        h = deduper.compute_hash(lead)
        assert len(h) == 64


class TestDeduplication:
    def test_is_duplicate_true_for_same_hash(self, deduper, lead_a):
        existing_hashes = {deduper.compute_hash(lead_a)}
        assert deduper.is_duplicate(lead_a, existing_hashes) is True

    def test_is_duplicate_false_for_new(self, deduper, lead_a, lead_b):
        existing_hashes = {deduper.compute_hash(lead_a)}
        assert deduper.is_duplicate(lead_b, existing_hashes) is False

    def test_filter_duplicates_removes_known(self, deduper, lead_a, lead_b):
        existing = {deduper.compute_hash(lead_a)}
        leads = [lead_a, lead_b]
        new_leads = deduper.filter_new(leads, existing)
        assert len(new_leads) == 1
        assert new_leads[0]["county"] == "san_diego"

    def test_filter_duplicates_within_batch(self, deduper, lead_a):
        leads = [lead_a, {**lead_a}]  # two identical leads in same batch
        new_leads = deduper.filter_new(leads, set())
        assert len(new_leads) == 1

    def test_empty_list_returns_empty(self, deduper):
        assert deduper.filter_new([], set()) == []
