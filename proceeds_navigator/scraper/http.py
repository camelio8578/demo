"""HTTP fetcher with retry and rate limiting."""
from __future__ import annotations

import os
import time

import httpx
import structlog

log = structlog.get_logger()

DEFAULT_HEADERS = {
    "User-Agent": os.getenv(
        "HTTP_USER_AGENT",
        "Mozilla/5.0 (compatible; GoldenStateClaimantAdvisors-Research/1.0)",
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


class HttpFetcher:
    def __init__(
        self,
        delay_seconds: float | None = None,
        max_retries: int | None = None,
        timeout: float | None = None,
    ):
        self.delay = delay_seconds if delay_seconds is not None else float(
            os.getenv("SCRAPE_DELAY_SECONDS", "2")
        )
        self.max_retries = max_retries if max_retries is not None else int(
            os.getenv("MAX_RETRIES", "3")
        )
        self.timeout = timeout if timeout is not None else float(
            os.getenv("REQUEST_TIMEOUT_SECONDS", "30")
        )
        self._last_request_time: dict[str, float] = {}

    def _rate_limit(self, domain: str) -> None:
        last = self._last_request_time.get(domain, 0)
        elapsed = time.monotonic() - last
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request_time[domain] = time.monotonic()

    def fetch(self, url: str) -> tuple[str, int]:
        """Fetch URL. Returns (html, status_code). Raises on unrecoverable error."""
        from urllib.parse import urlparse

        domain = urlparse(url).netloc

        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            self._rate_limit(domain)
            try:
                with httpx.Client(
                    headers=DEFAULT_HEADERS,
                    timeout=self.timeout,
                    follow_redirects=True,
                ) as client:
                    resp = client.get(url)
                    log.info(
                        "http_fetch",
                        url=url,
                        status=resp.status_code,
                        attempt=attempt + 1,
                    )
                    if resp.status_code == 429:
                        retry_after = int(resp.headers.get("Retry-After", 60))
                        log.warning("rate_limited", url=url, retry_after=retry_after)
                        time.sleep(retry_after)
                        continue
                    resp.raise_for_status()
                    return resp.text, resp.status_code
            except httpx.HTTPStatusError as exc:
                log.warning(
                    "http_status_error",
                    url=url,
                    status=exc.response.status_code,
                    attempt=attempt + 1,
                )
                last_exc = exc
            except httpx.RequestError as exc:
                wait = 2**attempt
                log.warning(
                    "http_request_error",
                    url=url,
                    error=str(exc),
                    retry_in=wait,
                )
                time.sleep(wait)
                last_exc = exc
        raise RuntimeError(
            f"Failed to fetch {url} after {self.max_retries} attempts: {last_exc}"
        )
