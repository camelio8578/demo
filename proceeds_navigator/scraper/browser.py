"""Playwright-based fetcher for JS-heavy pages."""
from __future__ import annotations

import os

import structlog

log = structlog.get_logger()


class BrowserFetcher:
    """Wraps Playwright for JS-rendered pages. Requires playwright install chromium."""

    def __init__(self, headless: bool | None = None):
        self.headless = headless if headless is not None else (
            os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
        )

    def fetch(self, url: str) -> tuple[str, int]:
        """Returns (html, 200) or raises RuntimeError."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            ) from exc

        log.info("browser_fetch", url=url, headless=self.headless)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page(
                user_agent=os.getenv(
                    "HTTP_USER_AGENT",
                    "Mozilla/5.0 (compatible; GoldenStateClaimantAdvisors-Research/1.0)",
                )
            )
            try:
                page.goto(url, timeout=30_000, wait_until="networkidle")
                html = page.content()
                return html, 200
            finally:
                browser.close()
