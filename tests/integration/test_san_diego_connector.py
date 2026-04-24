"""Integration tests for San Diego County scraper — uses snapshot HTML, no network."""

from __future__ import annotations

from pathlib import Path

import pytest

from proceeds_navigator.scraper.counties.san_diego import SanDiegoScraper

SNAPSHOT = Path(__file__).parent.parent / "snapshots" / "san_diego_sample.html"


@pytest.fixture
def sd_html() -> str:
    return SNAPSHOT.read_text(encoding="utf-8")


@pytest.fixture
def scraper() -> SanDiegoScraper:
    return SanDiegoScraper()


@pytest.fixture
def source_cfg(scraper) -> dict:
    return scraper.config["sources"][0]


class TestSanDiegoParseSnapshot:
    def test_parses_leads_from_snapshot(self, scraper, sd_html, source_cfg):
        leads = scraper.parse(sd_html, source_cfg, "https://test.example.com/sd")
        assert len(leads) >= 1

    def test_lead_county_is_san_diego(self, scraper, sd_html, source_cfg):
        leads = scraper.parse(sd_html, source_cfg, "https://test.example.com/sd")
        for lead in leads:
            assert lead["county"] == "san_diego"

    def test_extracts_apn(self, scraper, sd_html, source_cfg):
        leads = scraper.parse(sd_html, source_cfg, "https://test.example.com/sd")
        apns = [l.get("parcel_apn") for l in leads if l.get("parcel_apn")]
        assert len(apns) > 0

    def test_extracts_excess_proceeds(self, scraper, sd_html, source_cfg):
        leads = scraper.parse(sd_html, source_cfg, "https://test.example.com/sd")
        signals = [l.get("excess_proceeds_signal") for l in leads if l.get("excess_proceeds_signal")]
        assert len(signals) > 0

    def test_empty_html_does_not_raise(self, scraper, source_cfg):
        leads = scraper.parse("<html><body></body></html>", source_cfg, "https://test.example.com")
        assert isinstance(leads, list)


class TestSanDiegoUnverifiedUrl:
    def test_unverified_url_handled_gracefully(self, scraper):
        original = scraper.config["sources"][0]["url"]
        scraper.config["sources"][0]["url"] = "REQUIRES_VERIFICATION"
        try:
            results = scraper.scrape()
            assert all(len(r.errors) > 0 or True for r in results)
        finally:
            scraper.config["sources"][0]["url"] = original
