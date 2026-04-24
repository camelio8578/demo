"""San Diego County excess-proceeds scraper."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog
from bs4 import BeautifulSoup

from proceeds_navigator.scraper.base import BaseScraper, ScraperResult

log = structlog.get_logger()


class SanDiegoScraper(BaseScraper):
    county_key = "san_diego"

    def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        for source_cfg in self.config["sources"]:
            result = ScraperResult(
                county=self.county_key, source_name=source_cfg["name"]
            )
            url: str = source_cfg.get("url", "")

            if "REQUIRES_VERIFICATION" in url:
                log.warning(
                    "url_requires_verification",
                    county=self.county_key,
                    source=source_cfg["name"],
                    url=url,
                )
                result.errors.append(f"URL requires verification: {url}")
                results.append(result)
                continue

            try:
                html = self._fetch_html(url, source_cfg)
                result.snapshot_path = self.snapshot.save(
                    self.county_key, html, source_cfg["name"]
                )
                result.raw_leads.extend(self.parse(html, source_cfg, url))
            except Exception as exc:
                log.error(
                    "scrape_error",
                    county=self.county_key,
                    url=url,
                    error=str(exc),
                )
                result.errors.append(str(exc))

            result.completed_at = datetime.utcnow()
            results.append(result)
        return results

    def parse(self, html: str, source_cfg: dict, source_url: str) -> list[dict]:
        """Parse San Diego County HTML into raw lead dicts.

        Tries CSS selectors from config first; falls back to keyword matching.
        San Diego Treasurer-Tax Collector publishes a dedicated excess proceeds
        page and a separate tax-sales listing — both are handled via the same
        selector/fallback pattern driven by per-source config.
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
                    "county": self.county_key,
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
                        "county": self.county_key,
                        "source_type": source_cfg.get("source_type", "web_page"),
                        "source_url": source_url,
                        "page_title": page_title,
                        "excess_proceeds_signal": line,
                    }
                )
            if lines:
                log.info(
                    "keyword_fallback_used",
                    county=self.county_key,
                    matches=len(lines),
                )

        log.info("parse_complete", county=self.county_key, leads=len(leads))
        return leads
