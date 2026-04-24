"""Unit tests for lead scoring engine."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from proceeds_navigator.scoring.scorer import LeadScorer, ScoreResult


@pytest.fixture
def scorer():
    return LeadScorer()


@pytest.fixture
def base_lead():
    """A lead that will score in the mid range."""
    return {
        "county": "fresno",
        "source_type": "auction_list",
        "source_url": "https://www.fresnocounty.gov/tax-collector/test",
        "parcel_apn": "123-456-78",
        "situs_address": "1234 Main St, Fresno, CA 93720",
        "excess_proceeds_signal": "Excess proceeds: $12,500.00",
        "excess_proceeds_amount": 12500.0,
        "likely_claimant_type": "former_owner",
        "likely_claimant_name": "John Smith",
        "claimant_source_basis": "Named in auction source",
        "sale_date": date.today() - timedelta(days=90),
    }


class TestScorerOutputStructure:
    def test_returns_score_result(self, scorer, base_lead):
        result = scorer.score(base_lead)
        assert isinstance(result, ScoreResult)

    def test_score_in_range(self, scorer, base_lead):
        result = scorer.score(base_lead)
        assert 0.0 <= result.score <= 100.0

    def test_explanation_has_all_dimensions(self, scorer, base_lead):
        result = scorer.score(base_lead)
        dims = result.explanation
        assert "source_reliability" in dims
        assert "proceeds_existence" in dims
        assert "claimant_traceability" in dims
        assert "document_complexity" in dims
        assert "deadline_urgency" in dims

    def test_explanation_has_points_and_reason(self, scorer, base_lead):
        result = scorer.score(base_lead)
        for dim, detail in result.explanation.items():
            assert "points" in detail, f"Missing 'points' in {dim}"
            assert "reason" in detail, f"Missing 'reason' in {dim}"

    def test_priority_rank_set(self, scorer, base_lead):
        result = scorer.score(base_lead)
        assert result.priority_rank in (1, 2, 3, 4, 5)

    def test_risk_flag_set(self, scorer, base_lead):
        result = scorer.score(base_lead)
        assert result.legal_risk_flag in ("low", "medium", "high", "REQUIRES_LEGAL_REVIEW")


class TestScorerSourceReliability:
    def test_auction_list_scores_max(self, scorer, base_lead):
        base_lead["source_type"] = "auction_list"
        result = scorer.score(base_lead)
        assert result.explanation["source_reliability"]["points"] == 20

    def test_agenda_item_scores_15(self, scorer, base_lead):
        base_lead["source_type"] = "agenda_item"
        result = scorer.score(base_lead)
        assert result.explanation["source_reliability"]["points"] == 15

    def test_press_release_scores_10(self, scorer, base_lead):
        base_lead["source_type"] = "press_release"
        result = scorer.score(base_lead)
        assert result.explanation["source_reliability"]["points"] == 10

    def test_web_page_scores_5(self, scorer, base_lead):
        base_lead["source_type"] = "web_page"
        result = scorer.score(base_lead)
        assert result.explanation["source_reliability"]["points"] == 5


class TestScorerProceedsExistence:
    def test_stated_amount_scores_25(self, scorer, base_lead):
        base_lead["excess_proceeds_amount"] = 12500.0
        result = scorer.score(base_lead)
        assert result.explanation["proceeds_existence"]["points"] == 25

    def test_no_amount_keyword_only_scores_8(self, scorer, base_lead):
        base_lead["excess_proceeds_amount"] = None
        base_lead["excess_proceeds_signal"] = "excess proceeds available"
        result = scorer.score(base_lead)
        assert result.explanation["proceeds_existence"]["points"] == 8

    def test_no_signal_scores_low(self, scorer, base_lead):
        base_lead["excess_proceeds_amount"] = None
        base_lead["excess_proceeds_signal"] = "tax defaulted sale"
        result = scorer.score(base_lead)
        assert result.explanation["proceeds_existence"]["points"] <= 8


class TestScorerClaimantTraceability:
    def test_named_former_owner_scores_20(self, scorer, base_lead):
        base_lead["likely_claimant_type"] = "former_owner"
        base_lead["likely_claimant_name"] = "John Smith"
        result = scorer.score(base_lead)
        assert result.explanation["claimant_traceability"]["points"] == 20

    def test_unknown_claimant_scores_5(self, scorer, base_lead):
        base_lead["likely_claimant_type"] = "unknown"
        base_lead["likely_claimant_name"] = None
        result = scorer.score(base_lead)
        assert result.explanation["claimant_traceability"]["points"] == 5


class TestScorerDeadlineUrgency:
    def test_under_3_months_scores_15(self, scorer, base_lead):
        base_lead["sale_date"] = date.today() - timedelta(days=340)
        result = scorer.score(base_lead)
        assert result.explanation["deadline_urgency"]["points"] == 15

    def test_over_6_months_scores_5(self, scorer, base_lead):
        base_lead["sale_date"] = date.today() - timedelta(days=10)
        result = scorer.score(base_lead)
        assert result.explanation["deadline_urgency"]["points"] == 5

    def test_unknown_deadline_scores_0(self, scorer, base_lead):
        base_lead["sale_date"] = None
        result = scorer.score(base_lead)
        assert result.explanation["deadline_urgency"]["points"] == 0


class TestScorerPenalties:
    def test_missing_apn_applies_penalty(self, scorer, base_lead):
        base_lead["parcel_apn"] = None
        result_with = scorer.score(base_lead)
        base_lead["parcel_apn"] = "123-456-78"
        result_without = scorer.score(base_lead)
        assert result_with.score < result_without.score

    def test_lienholder_forces_legal_review(self, scorer, base_lead):
        base_lead["likely_claimant_type"] = "lienholder"
        result = scorer.score(base_lead)
        assert result.legal_risk_flag == "REQUIRES_LEGAL_REVIEW"

    def test_large_amount_forces_legal_review(self, scorer, base_lead):
        base_lead["excess_proceeds_amount"] = 100000.0
        result = scorer.score(base_lead)
        assert result.legal_risk_flag == "REQUIRES_LEGAL_REVIEW"


class TestScorerPriorityRank:
    def test_high_score_rank_1(self, scorer, base_lead):
        # Maximise score: auction list, stated amount, named owner, recent sale
        base_lead["source_type"] = "auction_list"
        base_lead["excess_proceeds_amount"] = 12500.0
        base_lead["likely_claimant_type"] = "former_owner"
        base_lead["likely_claimant_name"] = "John Smith"
        base_lead["parcel_apn"] = "123-456-78"
        base_lead["sale_date"] = date.today() - timedelta(days=10)
        result = scorer.score(base_lead)
        assert result.priority_rank in (1, 2)

    def test_minimal_lead_rank_4_or_5(self, scorer):
        minimal = {"county": "fresno", "source_type": "web_page"}
        result = scorer.score(minimal)
        assert result.priority_rank in (4, 5)
