"""Kelly Services job-board spider.

Kelly publishes a public job search at kellyservices.{country}/find-jobs
that emits schema.org JobPosting microdata, so we share the Randstad
parser pattern. Covers contract / direct-hire engineering and trades.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from datetime import UTC, datetime

import httpx
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from lip.config import get_settings
from lip.logging import get_logger
from lip.scraping.base import ScrapedPosting, Spider
from lip.scraping.sources.randstad import _parse as parse_jobposting_ldjson

logger = get_logger(__name__)


class _KellyBase(Spider):
    base_url: str = ""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = httpx.Client(
            timeout=15.0,
            headers={
                "User-Agent": self._settings.scrape_user_agent,
                "Accept": "text/html",
            },
            follow_redirects=True,
        )

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
    def _fetch(self, keyword: str) -> str:
        response = self._client.get(self.base_url, params={"keyword": keyword})
        response.raise_for_status()
        return response.text

    def crawl(self) -> Iterator[ScrapedPosting]:
        for kw in ("engineer", "construction", "project manager", "trades", "industrial"):
            try:
                payload = self._fetch(kw)
            except (httpx.HTTPError, RetryError):
                logger.exception("kelly_fetch_failed", source=self.source_name, kw=kw)
                continue
            yield from parse_jobposting_ldjson(
                payload, source_name=self.source_name, base_url=self.base_url,
                scraped_at=datetime.now(UTC),
            )


class KellyCanadaSpider(_KellyBase):
    source_name = "kelly_ca"
    description = "Kelly Services Canada — engineering, science, IT, light industrial."
    tier = 3
    countries = ("CA",)
    homepage = "https://www.kellyservices.ca"
    base_url = "https://www.kellyservices.ca/CA/En/Find-Jobs/"


class KellyUSSpider(_KellyBase):
    source_name = "kelly_us"
    description = "Kelly Services US — engineering, manufacturing, scientific contract roles."
    tier = 3
    countries = ("US",)
    homepage = "https://www.kellyservices.us"
    base_url = "https://www.kellyservices.us/find-jobs/"
