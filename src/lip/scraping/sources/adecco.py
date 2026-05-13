"""Adecco / Akkodis job-board spider.

Adecco operates global staffing; Akkodis (the rebranded tech/engineering
arm) is the relevant brand for industrial placements. Both expose JSON
API search endpoints.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from datetime import UTC, datetime

import httpx
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from lip.logging import get_logger
from lip.scraping.base import ScrapedPosting, Spider
from lip.scraping.http_client import make_http_client

logger = get_logger(__name__)


class _AdeccoBase(Spider):
    base_url: str = ""

    def __init__(self) -> None:
        self._client = make_http_client(accept="application/json")

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
    def _fetch_page(self, page: int) -> dict:
        response = self._client.get(self.base_url, params={"page": page, "category": "industrial-engineering"})
        response.raise_for_status()
        return response.json() if response.headers.get("content-type", "").startswith("application/json") else {}

    def crawl(self) -> Iterator[ScrapedPosting]:
        for page in range(1, 6):
            try:
                payload = self._fetch_page(page)
            except (httpx.HTTPError, RetryError, ValueError):
                logger.exception("adecco_fetch_failed", source=self.source_name, page=page)
                break
            jobs = payload.get("jobs") or payload.get("results") or []
            if not jobs:
                break
            for j in jobs:
                yield ScrapedPosting(
                    source=self.source_name,
                    source_posting_id=str(j.get("id") or j.get("jobId") or j.get("url", ""))[:255],
                    source_url=j.get("url") or self.base_url,
                    raw_title=j.get("title"),
                    company_raw=j.get("client") or j.get("companyName"),
                    location_raw=j.get("location"),
                    salary_raw=j.get("salary"),
                    description_text=j.get("description"),
                    raw_payload=str(j),
                    scraped_at=datetime.now(UTC),
                )


class AdeccoCanadaSpider(_AdeccoBase):
    source_name = "adecco_ca"
    description = "Adecco Canada — light industrial, manufacturing, trades."
    tier = 3
    countries = ("CA",)
    homepage = "https://www.adecco.ca"
    base_url = "https://www.adecco.ca/api/jobs/search"


class AdeccoUSSpider(_AdeccoBase):
    source_name = "adecco_us"
    description = "Adecco US."
    tier = 3
    countries = ("US",)
    homepage = "https://www.adeccousa.com"
    base_url = "https://www.adeccousa.com/api/jobs/search"


class AkkodisSpider(_AdeccoBase):
    source_name = "akkodis_global"
    description = "Akkodis (Adecco engineering arm) — engineering / IT consulting placements."
    tier = 3
    countries = ("CA", "US")
    homepage = "https://www.akkodis.com"
    base_url = "https://www.akkodis.com/api/jobs/search"
