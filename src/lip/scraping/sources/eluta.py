"""Eluta.ca spider.

Eluta is a Canadian job-board aggregator that crawls 30,000+ employer
career pages and exposes search results as HTML with embedded
schema.org JobPosting blocks.
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


class ElutaSpider(Spider):
    source_name = "eluta_ca"
    description = "Eluta.ca — Canadian employer career-page aggregator."
    tier = 3
    countries = ("CA",)
    homepage = "https://www.eluta.ca"
    base_url = "https://www.eluta.ca/search"

    KEYWORDS = (
        "construction project manager",
        "superintendent",
        "estimator",
        "process engineer",
        "completions engineer",
        "pipefitter",
        "millwright",
    )

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = httpx.Client(
            timeout=15.0,
            headers={"User-Agent": self._settings.scrape_user_agent},
            follow_redirects=True,
        )

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
    def _fetch(self, q: str) -> str:
        r = self._client.get(self.base_url, params={"q": q})
        r.raise_for_status()
        return r.text

    def crawl(self) -> Iterator[ScrapedPosting]:
        for kw in self.KEYWORDS:
            try:
                payload = self._fetch(kw)
            except (httpx.HTTPError, RetryError):
                logger.exception("eluta_fetch_failed", kw=kw)
                continue
            yield from parse_jobposting_ldjson(
                payload, source_name=self.source_name,
                base_url=self.base_url, scraped_at=datetime.now(UTC),
            )
