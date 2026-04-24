"""Integration tests for Los Angeles County scraper — snapshot-based, no network."""

from __future__ import annotations

import pytest

from proceeds_navigator.scraper.counties.los_angeles import LosAngelesScraper


@pytest.fixture
def scraper() -> LosAngelesScraper:
    return LosAngelesScraper()


@pytest.fixture
def source_cfg(scraper) -> dict:
    return scraper.config["sources"][0]


SYNTHETIC_HTML = """<!DOCTYPE html>
<!-- SYNTHETIC TEST FIXTURE — NOT REAL COUNTY DATA -->
<html><head><title>Los Angeles County Excess Proceeds</title></head>
<body>
  <div class="excess-proceeds">
    <table class="ep-list">
      <thead><tr><th>APN</th><th>Property Address</th><th>Sale Date</th><th>Excess Proceeds</th></tr></thead>
      <tbody>
        <tr><td>900-090-09</td><td>900 Sample Rd, Los Angeles, CA 90001</td><td>November 15, 2025</td><td>$45,000.00</td></tr>
        <tr><td>101-010-10</td><td>1010 Test Blvd, Compton, CA 90220</td><td>November 15, 2025</td><td>$7,300.00</td></tr>
      </tbody>
    </table>
  </div>
</body></html>"""


class TestLosAngelesParseHTML:
    def test_parses_leads(self, scraper, source_cfg):
        leads = scraper.parse(SYNTHETIC_HTML, source_cfg, "https://test.example.com/la")
        assert len(leads) >= 1

    def test_lead_county_is_los_angeles(self, scraper, source_cfg):
        leads = scraper.parse(SYNTHETIC_HTML, source_cfg, "https://test.example.com/la")
        for lead in leads:
            assert lead["county"] == "los_angeles"

    def test_extracts_large_amount(self, scraper, source_cfg):
        leads = scraper.parse(SYNTHETIC_HTML, source_cfg, "https://test.example.com/la")
        signals = [l.get("excess_proceeds_signal") for l in leads if l.get("excess_proceeds_signal")]
        assert any("45,000" in (s or "") or "45000" in (s or "") for s in signals)

    def test_empty_html_returns_list(self, scraper, source_cfg):
        leads = scraper.parse("<html><body></body></html>", source_cfg, "https://test.example.com")
        assert isinstance(leads, list)

    def test_keyword_fallback_on_no_table(self, scraper, source_cfg):
        html = "<html><body><p>Excess proceeds available for tax defaulted property APN 111-111-11.</p></body></html>"
        leads = scraper.parse(html, source_cfg, "https://test.example.com")
        assert isinstance(leads, list)


class TestLosAngelesUnverifiedUrl:
    def test_unverified_url_error_not_exception(self, scraper):
        original = scraper.config["sources"][0]["url"]
        scraper.config["sources"][0]["url"] = "REQUIRES_VERIFICATION"
        try:
            results = scraper.scrape()
            assert len(results) > 0
        finally:
            scraper.config["sources"][0]["url"] = original
