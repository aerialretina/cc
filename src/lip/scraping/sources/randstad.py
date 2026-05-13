"""Randstad Canada / US / UK careers spiders.

Randstad publishes structured job feeds on its country sites. We hit the
public search endpoint and extract postings tagged with industrial NOCs
or skill keywords. Bot detection is light but rate-limited; default
cadence is daily.
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

INDUSTRIAL_KEYWORDS = (
    "engineer", "superintendent", "project manager", "estimator",
    "pipefitter", "welder", "electrician", "millwright", "process",
)


class _RandstadBase(Spider):
    base_url: str = ""
    country_code: str = ""
    max_keywords: int = len(INDUSTRIAL_KEYWORDS)

    def __init__(self) -> None:
        self._client = make_http_client()

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
    def _fetch(self, keyword: str) -> str:
        response = self._client.get(self.base_url, params={"q": keyword})
        response.raise_for_status()
        return response.text

    def crawl(self) -> Iterator[ScrapedPosting]:
        for kw in INDUSTRIAL_KEYWORDS[: self.max_keywords]:
            try:
                payload = self._fetch(kw)
            except (httpx.HTTPError, RetryError):
                logger.exception("randstad_fetch_failed", source=self.source_name, kw=kw)
                continue
            yield from _parse(payload, source_name=self.source_name, base_url=self.base_url, scraped_at=datetime.now(UTC))


def _parse(payload: str, *, source_name: str, base_url: str, scraped_at: datetime) -> list[ScrapedPosting]:
    """Pull postings from Randstad's HTML results page.

    The parser uses the schema.org JobPosting microdata that all Randstad
    sites emit. Returns an empty list on shapes we don't recognize so a
    layout change doesn't blow up the run.
    """
    import json
    import re

    out: list[ScrapedPosting] = []
    for match in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', payload, re.DOTALL):
        try:
            blob = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        candidates = blob if isinstance(blob, list) else [blob]
        for c in candidates:
            if not isinstance(c, dict) or c.get("@type") != "JobPosting":
                continue
            sid = str(c.get("identifier", c.get("url", "")))[:255]
            if not sid:
                continue
            out.append(ScrapedPosting(
                source=source_name,
                source_posting_id=sid,
                source_url=str(c.get("url", base_url)),
                raw_title=c.get("title"),
                company_raw=(c.get("hiringOrganization") or {}).get("name") if isinstance(c.get("hiringOrganization"), dict) else None,
                location_raw=_loc(c.get("jobLocation")),
                description_text=c.get("description"),
                raw_payload=json.dumps(c),
                scraped_at=scraped_at,
            ))
    return out


def _loc(value) -> str | None:
    if not value:
        return None
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, dict):
        addr = value.get("address") or {}
        if isinstance(addr, dict):
            parts = [addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry")]
            return ", ".join(p for p in parts if p)
    return None


class RandstadCanadaSpider(_RandstadBase):
    source_name = "randstad_ca"
    description = "Randstad Canada — staffing agency, industrial / engineering / trades placements."
    tier = 3
    countries = ("CA",)
    homepage = "https://www.randstad.ca"
    base_url = "https://www.randstad.ca/jobs/"


class RandstadUSSpider(_RandstadBase):
    source_name = "randstad_us"
    description = "Randstad US — engineering and skilled-trades placements."
    tier = 3
    countries = ("US",)
    homepage = "https://www.randstadusa.com"
    base_url = "https://www.randstadusa.com/jobs/search/"
