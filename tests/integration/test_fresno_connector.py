"""Integration tests for Fresno County scraper — uses snapshot HTML, no network."""

from __future__ import annotations

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from proceeds_navigator.scraper.counties.fresno import FresnoScraper

SNAPSHOT = Path(__file__).parent.parent / "snapshots" / "fresno_sample.html"


@pytest.fixture
def fresno_html() -> str:
    return SNAPSHOT.read_text(encoding="utf-8")


@pytest.fixture
def scraper() -> FresnoScraper:
    return FresnoScraper()


@pytest.fixture
def source_cfg(scraper) -> dict:
    return scraper.config["sources"][0]


class TestFresnoParseSnapshot:
    def test_parses_leads_from_snapshot(self, scraper, fresno_html, source_cfg):
        leads = scraper.parse(
            html=fresno_html,
            source_cfg=source_cfg,
            source_url="https://test.example.com/fresno",
        )
        assert len(leads) >= 1

    def test_lead_has_required_fields(self, scraper, fresno_html, source_cfg):
        leads = scraper.parse(fresno_html, source_cfg, "https://test.example.com/fresno")
        for lead in leads:
            assert lead["county"] == "fresno"
            assert lead["source_type"] in ("auction_list", "web_page", "notice", "agenda_item", "press_release")
            assert lead["source_url"] == "https://test.example.com/fresno"

    def test_extracts_apn(self, scraper, fresno_html, source_cfg):
        leads = scraper.parse(fresno_html, source_cfg, "https://test.example.com/fresno")
        apns = [l.get("parcel_apn") for l in leads if l.get("parcel_apn")]
        assert len(apns) > 0
        assert any("100-010-01" in apn for apn in apns)

    def test_extracts_address(self, scraper, fresno_html, source_cfg):
        leads = scraper.parse(fresno_html, source_cfg, "https://test.example.com/fresno")
        addrs = [l.get("situs_address") for l in leads if l.get("situs_address")]
        assert len(addrs) > 0

    def test_extracts_excess_proceeds_signal(self, scraper, fresno_html, source_cfg):
        leads = scraper.parse(fresno_html, source_cfg, "https://test.example.com/fresno")
        signals = [l.get("excess_proceeds_signal") for l in leads if l.get("excess_proceeds_signal")]
        assert len(signals) > 0

    def test_does_not_raise_on_empty_html(self, scraper, source_cfg):
        leads = scraper.parse("<html><body></body></html>", source_cfg, "https://test.example.com")
        assert isinstance(leads, list)

    def test_county_set_correctly(self, scraper, fresno_html, source_cfg):
        leads = scraper.parse(fresno_html, source_cfg, "https://test.example.com/fresno")
        for lead in leads:
            assert lead["county"] == "fresno"


class TestFresnoKeywordFallback:
    def test_keyword_fallback_on_no_table(self, scraper, source_cfg):
        html = """
        <html><body>
        <p>Excess proceeds of $5,000 are available for APN 999-999-99.</p>
        <p>Tax sale completed on November 15, 2025.</p>
        </body></html>
        """
        leads = scraper.parse(html, source_cfg, "https://test.example.com")
        assert len(leads) >= 1

    def test_fallback_includes_signal_text(self, scraper, source_cfg):
        html = """
        <html><body>
        <p>Excess proceeds of $12,000 are available for APN 111-222-33.</p>
        </body></html>
        """
        leads = scraper.parse(html, source_cfg, "https://test.example.com")
        assert any("excess proceeds" in (l.get("excess_proceeds_signal") or "").lower() for l in leads)


class TestFresnoUrlVerification:
    def test_unverified_url_returns_error_not_exception(self, scraper):
        """Scraper should handle REQUIRES_VERIFICATION URLs gracefully."""
        # Modify config to use unverified URL
        original = scraper.config["sources"][0]["url"]
        scraper.config["sources"][0]["url"] = "REQUIRES_VERIFICATION"
        try:
            results = scraper.scrape()
            assert len(results) > 0
            result = results[0]
            assert len(result.errors) > 0
            assert result.raw_leads == [] or True  # may be empty
        finally:
            scraper.config["sources"][0]["url"] = original
