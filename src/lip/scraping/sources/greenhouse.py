"""Greenhouse ATS spider.

Public, unauthenticated JSON API:

  GET https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true

Returns ``{jobs: [{id, title, location, departments, offices,
absolute_url, ...}]}``. Used widely by tech-leaning firms; less common
for traditional industrial but worth covering.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import httpx
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from lip.logging import get_logger
from lip.scraping.base import ScrapedPosting, Spider
from lip.scraping.http_client import make_http_client

logger = get_logger(__name__)


class _GreenhouseBase(Spider):
    company_slug: str = ""
    company_label: str = ""

    def __init__(self) -> None:
        self._client = make_http_client(accept="application/json")

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._client.close()

    @property
    def endpoint(self) -> str:
        return f"https://boards-api.greenhouse.io/v1/boards/{self.company_slug}/jobs?content=true"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
    def _fetch(self) -> dict[str, Any]:
        resp = self._client.get(self.endpoint)
        resp.raise_for_status()
        return resp.json()

    def crawl(self) -> Iterator[ScrapedPosting]:
        try:
            payload = self._fetch()
        except (httpx.HTTPError, RetryError):
            logger.exception("greenhouse_fetch_failed", source=self.source_name)
            return
        for j in payload.get("jobs", []):
            yield ScrapedPosting(
                source=self.source_name,
                source_posting_id=str(j.get("id", ""))[:255],
                source_url=j.get("absolute_url") or self.endpoint,
                raw_title=j.get("title"),
                company_raw=self.company_label or self.company_slug,
                location_raw=(j.get("location") or {}).get("name") if isinstance(j.get("location"), dict) else j.get("location"),
                description_text=j.get("content"),
                raw_payload=str(j),
                extra={"greenhouse_slug": self.company_slug,
                       "departments": [d.get("name") for d in j.get("departments", []) if isinstance(d, dict)]},
                scraped_at=datetime.now(UTC),
            )


# ---- concrete employers --------------------------------------------------

class StantecGreenhouseSpider(_GreenhouseBase):
    source_name = "greenhouse_stantec"
    description = "Stantec — Greenhouse ATS (if active)."
    tier = 1
    countries = ("CA", "US")
    homepage = "https://stantec.com/careers"
    company_slug = "stantec"
    company_label = "Stantec"


class WSPGreenhouseSpider(_GreenhouseBase):
    source_name = "greenhouse_wsp"
    description = "WSP — Greenhouse ATS (if active)."
    tier = 1
    countries = ("CA",)
    homepage = "https://www.wsp.com/en-ca/careers"
    company_slug = "wsp"
    company_label = "WSP Canada"
