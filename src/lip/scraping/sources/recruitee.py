"""Recruitee ATS spider.

Recruitee is popular at SMBs and mid-market (especially European-origin
firms). Public JSON board endpoint per company:

  GET https://{slug}.recruitee.com/api/offers/

Returns ``{offers: [{id, title, location, city, country,
created_at, careers_url, description, ...}]}``.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from datetime import UTC, date, datetime
from typing import Any

import httpx
from dateutil import parser as dateparser
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from lip.logging import get_logger
from lip.scraping.base import ScrapedPosting, Spider
from lip.scraping.http_client import make_http_client

logger = get_logger(__name__)


class _RecruiteeBase(Spider):
    slug: str = ""
    company_label: str = ""

    def __init__(self) -> None:
        self._client = make_http_client(accept="application/json")

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
    def _fetch(self) -> dict[str, Any]:
        url = f"https://{self.slug}.recruitee.com/api/offers/"
        resp = self._client.get(url)
        resp.raise_for_status()
        return resp.json()

    def crawl(self) -> Iterator[ScrapedPosting]:
        try:
            payload = self._fetch()
        except (httpx.HTTPError, RetryError):
            logger.exception("recruitee_fetch_failed", source=self.source_name)
            return
        for o in payload.get("offers", []):
            posted: date | None = None
            created = o.get("created_at")
            if isinstance(created, str):
                try:
                    posted = dateparser.parse(created).date()
                except (ValueError, TypeError):
                    posted = None
            yield ScrapedPosting(
                source=self.source_name,
                source_posting_id=str(o.get("id", ""))[:255],
                source_url=o.get("careers_url") or o.get("url") or "",
                raw_title=o.get("title"),
                company_raw=self.company_label or self.slug,
                location_raw=", ".join(s for s in (o.get("city"), o.get("country"), o.get("location")) if s),
                posted_date=posted,
                description_text=o.get("description"),
                raw_payload=str(o),
                extra={"recruitee_slug": self.slug, "department": o.get("department")},
                scraped_at=datetime.now(UTC),
            )


class RecruiteeExampleSpider(_RecruiteeBase):
    """Placeholder; swap `slug` to any Recruitee-using SMB / mid-market firm."""
    source_name = "recruitee_example"
    description = "Recruitee ATS — replace `slug` with a real Recruitee-using employer."
    tier = 1
    countries = ("CA",)
    homepage = "https://recruitee.com"
    slug = "recruitee"
    company_label = "Recruitee"
