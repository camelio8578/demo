"""Unit tests for ETL normalizer."""

from __future__ import annotations

import pytest
from datetime import date

from proceeds_navigator.etl.normalizer import Normalizer, ParseError


class TestNormalizerBasic:
    def setup_method(self):
        self.n = Normalizer()

    def test_normalize_minimal_valid_record(self, sample_raw_lead):
        result = self.n.normalize(sample_raw_lead)
        assert result["county"] == "fresno"
        assert result["source_type"] == "auction_list"
        assert result["parcel_apn"] == "123-456-78"

    def test_normalize_strips_whitespace(self):
        raw = {
            "county": "  fresno  ",
            "source_type": "auction_list",
            "parcel_apn": " 123-456-78 ",
            "situs_address": "  1234 Main St  ",
        }
        result = self.n.normalize(raw)
        assert result["county"] == "fresno"
        assert result["parcel_apn"] == "123-456-78"
        assert result["situs_address"] == "1234 Main St"

    def test_normalize_county_validation(self):
        raw = {"county": "invalid_county", "source_type": "auction_list"}
        with pytest.raises(ParseError, match="county"):
            self.n.normalize(raw)

    def test_normalize_requires_county(self):
        raw = {"source_type": "auction_list"}
        with pytest.raises(ParseError, match="county"):
            self.n.normalize(raw)

    def test_normalize_requires_source_type(self):
        raw = {"county": "fresno"}
        with pytest.raises(ParseError, match="source_type"):
            self.n.normalize(raw)


class TestNormalizerDateParsing:
    def setup_method(self):
        self.n = Normalizer()

    def test_parse_iso_date(self):
        raw = {"county": "fresno", "source_type": "auction_list", "sale_date_raw": "2025-11-15"}
        result = self.n.normalize(raw)
        assert result["sale_date"] == date(2025, 11, 15)

    def test_parse_us_date_format(self):
        raw = {"county": "fresno", "source_type": "auction_list", "sale_date_raw": "11/15/2025"}
        result = self.n.normalize(raw)
        assert result["sale_date"] == date(2025, 11, 15)

    def test_parse_written_date(self):
        raw = {
            "county": "fresno",
            "source_type": "auction_list",
            "sale_date_raw": "November 15, 2025",
        }
        result = self.n.normalize(raw)
        assert result["sale_date"] == date(2025, 11, 15)

    def test_invalid_date_returns_none(self):
        raw = {
            "county": "fresno",
            "source_type": "auction_list",
            "sale_date_raw": "not-a-date",
        }
        result = self.n.normalize(raw)
        assert result["sale_date"] is None

    def test_missing_date_returns_none(self):
        raw = {"county": "fresno", "source_type": "auction_list"}
        result = self.n.normalize(raw)
        assert result.get("sale_date") is None


class TestNormalizerAmountParsing:
    def setup_method(self):
        self.n = Normalizer()

    def test_parse_dollar_amount(self):
        raw = {
            "county": "fresno",
            "source_type": "auction_list",
            "excess_proceeds_signal": "Excess proceeds: $12,500.00",
        }
        result = self.n.normalize(raw)
        assert result["excess_proceeds_amount"] == pytest.approx(12500.0)

    def test_parse_amount_no_dollar_sign(self):
        raw = {
            "county": "fresno",
            "source_type": "auction_list",
            "excess_proceeds_signal": "Excess proceeds: 8750.50",
        }
        result = self.n.normalize(raw)
        assert result["excess_proceeds_amount"] == pytest.approx(8750.50)

    def test_no_amount_returns_none(self):
        raw = {
            "county": "fresno",
            "source_type": "auction_list",
            "excess_proceeds_signal": "Tax defaulted sale",
        }
        result = self.n.normalize(raw)
        assert result["excess_proceeds_amount"] is None

    def test_missing_signal_returns_none(self):
        raw = {"county": "fresno", "source_type": "auction_list"}
        result = self.n.normalize(raw)
        assert result["excess_proceeds_amount"] is None


class TestNormalizerClaimantType:
    def setup_method(self):
        self.n = Normalizer()

    def test_defaults_to_unknown(self):
        raw = {"county": "fresno", "source_type": "auction_list"}
        result = self.n.normalize(raw)
        assert result["likely_claimant_type"] == "unknown"

    def test_former_owner_when_name_present(self):
        raw = {
            "county": "fresno",
            "source_type": "auction_list",
            "likely_claimant_name": "Jane Doe",
        }
        result = self.n.normalize(raw)
        assert result["likely_claimant_type"] == "former_owner"

    def test_explicit_claimant_type_preserved(self):
        raw = {
            "county": "fresno",
            "source_type": "auction_list",
            "likely_claimant_type": "lienholder",
            "likely_claimant_name": "First National Bank",
        }
        result = self.n.normalize(raw)
        assert result["likely_claimant_type"] == "lienholder"


class TestNormalizerApnNormalization:
    def setup_method(self):
        self.n = Normalizer()

    def test_apn_cleaned(self):
        raw = {"county": "fresno", "source_type": "auction_list", "parcel_apn": "123-456-78-0"}
        result = self.n.normalize(raw)
        assert result["parcel_apn"] is not None
        assert " " not in result["parcel_apn"]

    def test_apn_none_when_missing(self):
        raw = {"county": "fresno", "source_type": "auction_list"}
        result = self.n.normalize(raw)
        assert result.get("parcel_apn") is None
