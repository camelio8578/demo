"""Integration tests for Sacramento County scraper — snapshot-based, no network."""

from __future__ import annotations

import pytest

from proceeds_navigator.scraper.counties.sacramento import SacramentoScraper


@pytest.fixture
def scraper() -> SacramentoScraper:
    return SacramentoScraper()


@pytest.fixture
def source_cfg(scraper) -> dict:
    return scraper.config["sources"][0]


SYNTHETIC_HTML = """<!DOCTYPE html>
<!-- SYNTHETIC TEST FIXTURE — NOT REAL COUNTY DATA -->
<html><head><title>Sacramento County Tax Sale Results</title></head>
<body>
  <table class="tax-sale">
    <thead><tr><th>APN</th><th>Address</th><th>Sale Date</th><th>Excess Proceeds</th></tr></thead>
    <tbody>
      <tr><td>600-060-06</td><td>600 Synth St, Sacramento, CA 95814</td><td>2025-10-01</td><td>$9,800.00</td></tr>
      <tr><td>700-070-07</td><td>700 Mock Ave, Sacramento, CA 95820</td><td>2025-10-01</td><td>$1,500.00</td></tr>
    </tbody>
  </table>
</body></html>"""


class TestSacramentoParseHTML:
    def test_parses_leads(self, scraper, source_cfg):
        leads = scraper.parse(SYNTHETIC_HTML, source_cfg, "https://test.example.com/sac")
        assert len(leads) >= 1

    def test_lead_county_is_sacramento(self, scraper, source_cfg):
        leads = scraper.parse(SYNTHETIC_HTML, source_cfg, "https://test.example.com/sac")
        for lead in leads:
            assert lead["county"] == "sacramento"

    def test_extracts_apn(self, scraper, source_cfg):
        leads = scraper.parse(SYNTHETIC_HTML, source_cfg, "https://test.example.com/sac")
        apns = [l.get("parcel_apn") for l in leads if l.get("parcel_apn")]
        assert len(apns) > 0

    def test_empty_html_returns_list(self, scraper, source_cfg):
        leads = scraper.parse("<html><body></body></html>", source_cfg, "https://test.example.com")
        assert isinstance(leads, list)


class TestSacramentoKeywordFallback:
    def test_fallback_extracts_excess_proceeds_lines(self, scraper, source_cfg):
        html = "<html><body><p>Excess proceeds of $4,500 available for APN 800-080-08.</p></body></html>"
        leads = scraper.parse(html, source_cfg, "https://test.example.com")
        assert len(leads) >= 1


class TestSacramentoUnverifiedUrl:
    def test_unverified_url_error_not_exception(self, scraper):
        original = scraper.config["sources"][0]["url"]
        scraper.config["sources"][0]["url"] = "REQUIRES_VERIFICATION"
        try:
            results = scraper.scrape()
            assert len(results) > 0
        finally:
            scraper.config["sources"][0]["url"] = original
