"""Base scraper class."""
from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
import yaml
from bs4 import BeautifulSoup

from proceeds_navigator.scraper.browser import BrowserFetcher
from proceeds_navigator.scraper.http import HttpFetcher
from proceeds_navigator.scraper.snapshot import SnapshotSaver

log = structlog.get_logger()


def load_county_config(county_key: str) -> dict:
    config_path = Path(__file__).parent.parent / "config" / "counties.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return data["counties"][county_key]


class ScraperResult:
    def __init__(self, county: str, source_name: str):
        self.county = county
        self.source_name = source_name
        self.raw_leads: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self.snapshot_path: Path | None = None
        self.started_at: datetime = datetime.utcnow()
        self.completed_at: datetime | None = None

    @property
    def status(self) -> str:
        if not self.errors and self.raw_leads:
            return "success"
        if self.errors and self.raw_leads:
            return "partial"
        return "failed"


class BaseScraper(ABC):
    county_key: str  # must be set by subclass

    def __init__(self) -> None:
        self.config = load_county_config(self.county_key)
        self.http = HttpFetcher()
        self.browser = BrowserFetcher()
        self.snapshot = SnapshotSaver()

    def _fetch_html(self, url: str, source_cfg: dict) -> str:
        """Try static fetch first; fall back to browser if needed."""
        method = source_cfg.get("scrape_method", "static")
        if method == "browser":
            html, _ = self.browser.fetch(url)
            return html
        try:
            html, _ = self.http.fetch(url)
            # Detect JS-only page (no meaningful content)
            if self._is_js_only(html):
                log.info("js_only_detected_falling_back", url=url)
                html, _ = self.browser.fetch(url)
            return html
        except Exception as exc:
            log.warning("static_fetch_failed_trying_browser", url=url, error=str(exc))
            html, _ = self.browser.fetch(url)
            return html

    def _is_js_only(self, html: str) -> bool:
        """Heuristic: if <body> has <10 words of visible text, likely JS-rendered."""
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(separator=" ", strip=True)
        return len(text.split()) < 10

    def _keyword_fallback(self, html: str, keywords: list[str]) -> list[str]:
        """Extract lines containing any keyword — used when selectors fail."""
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(separator="\n", strip=True)
        matches = []
        for line in text.splitlines():
            if any(kw.lower() in line.lower() for kw in keywords):
                matches.append(line.strip())
        return matches

    def _try_selectors(
        self, soup: BeautifulSoup, selector_list: list[str]
    ) -> Any:
        """Try each selector; return first match or None."""
        for sel in selector_list:
            result = soup.select_one(sel)
            if result:
                return result
        return None

    def _extract_amount(self, text: str | None) -> float | None:
        if not text:
            return None
        match = re.search(r"\$?\s*([\d,]+\.?\d*)", text.replace(",", ""))
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                return None
        return None

    def _parse_table(
        self,
        html: str,
        source_cfg: dict,
        source_url: str,
        county: str,
    ) -> list[dict[str, Any]]:
        """
        Shared table-parsing logic used by all county scrapers.

        Tries CSS selectors from config first; falls back to keyword matching.
        Returns a list of raw lead dicts.
        """
        soup = BeautifulSoup(html, "lxml")
        leads: list[dict[str, Any]] = []
        page_title: str | None = (
            soup.find("title").get_text(strip=True) if soup.find("title") else None
        )

        sel_cfg = source_cfg.get("selectors", {})
        table_selectors: list[str] = sel_cfg.get("table", [])

        table = None
        for sel in table_selectors:
            table = soup.select_one(sel)
            if table:
                break

        if table:
            rows = table.find_all("tr")
            for row in rows[1:]:  # skip header row
                cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                if len(cells) < 2:
                    continue

                apn_cols: list[int] = sel_cfg.get("apn_col", [0])
                addr_cols: list[int] = sel_cfg.get("address_col", [1])
                date_cols: list[int] = sel_cfg.get("sale_date_col", [2])
                amt_cols: list[int] = sel_cfg.get("amount_col", [3])

                lead: dict[str, Any] = {
                    "county": county,
                    "source_type": source_cfg.get("source_type", "web_page"),
                    "source_url": source_url,
                    "page_title": page_title,
                    "parcel_apn": next(
                        (cells[i] for i in apn_cols if i < len(cells) and cells[i]),
                        None,
                    ),
                    "situs_address": next(
                        (cells[i] for i in addr_cols if i < len(cells) and cells[i]),
                        None,
                    ),
                    "sale_date_raw": next(
                        (cells[i] for i in date_cols if i < len(cells) and cells[i]),
                        None,
                    ),
                    "excess_proceeds_signal": next(
                        (cells[i] for i in amt_cols if i < len(cells) and cells[i]),
                        None,
                    ),
                }
                if any(
                    lead.get(k)
                    for k in ("parcel_apn", "situs_address", "excess_proceeds_signal")
                ):
                    leads.append(lead)

        if not leads:
            keywords: list[str] = source_cfg.get(
                "keyword_fallback", ["excess proceeds"]
            )
            lines = self._keyword_fallback(html, keywords)
            for line in lines:
                leads.append(
                    {
                        "county": county,
                        "source_type": source_cfg.get("source_type", "web_page"),
                        "source_url": source_url,
                        "page_title": page_title,
                        "excess_proceeds_signal": line,
                    }
                )
            if lines:
                log.info(
                    "keyword_fallback_used", county=county, matches=len(lines)
                )

        log.info("parse_complete", county=county, leads=len(leads))
        return leads

    @abstractmethod
    def scrape(self) -> list[ScraperResult]:
        """Scrape all configured sources. Returns list of results (one per source)."""
        ...

    @abstractmethod
    def parse(self, html: str, source_cfg: dict, source_url: str) -> list[dict]:
        """Parse HTML into list of raw lead dicts."""
        ...
