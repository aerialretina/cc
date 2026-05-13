"""Ashby ATS spider — newer platform popular at growth-stage / mid-market.

Public job-board JSON endpoint:

  GET https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true

Returns ``{apiVersion, jobs: [{id, title, location, department,
employmentType, secondaryLocations, compensation, jobUrl,
publishedDate}]}``. No auth.
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


class _AshbyBase(Spider):
    slug: str = ""
    company_label: str = ""

    def __init__(self) -> None:
        self._client = make_http_client(accept="application/json")

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
    def _fetch(self) -> dict[str, Any]:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{self.slug}"
        resp = self._client.get(url, params={"includeCompensation": "true"})
        resp.raise_for_status()
        return resp.json()

    def crawl(self) -> Iterator[ScrapedPosting]:
        try:
            payload = self._fetch()
        except (httpx.HTTPError, RetryError):
            logger.exception("ashby_fetch_failed", source=self.source_name)
            return
        for j in payload.get("jobs", []):
            posted: date | None = None
            pub = j.get("publishedDate") or j.get("publishedAt")
            if isinstance(pub, str):
                try:
                    posted = dateparser.parse(pub).date()
                except (ValueError, TypeError):
                    posted = None
            comp = j.get("compensation") or {}
            tiers = comp.get("compensationTierSummary") if isinstance(comp, dict) else None
            salary_raw = ", ".join(tiers) if isinstance(tiers, list) else None
            yield ScrapedPosting(
                source=self.source_name,
                source_posting_id=str(j.get("id", ""))[:255],
                source_url=j.get("jobUrl") or j.get("applyUrl") or "",
                raw_title=j.get("title"),
                company_raw=self.company_label or self.slug,
                location_raw=j.get("location"),
                posted_date=posted,
                salary_raw=salary_raw,
                job_type=j.get("employmentType"),
                description_text=j.get("descriptionPlain") or j.get("description"),
                raw_payload=str(j),
                extra={"ashby_slug": self.slug, "department": j.get("department")},
                scraped_at=datetime.now(UTC),
            )


class AshbyExampleSpider(_AshbyBase):
    """Placeholder concrete spider — substitute any Ashby-using employer."""
    source_name = "ashby_example"
    description = "Ashby ATS — replace `slug` with a real Ashby-using employer."
    tier = 1
    countries = ("CA", "US")
    homepage = "https://www.ashbyhq.com"
    slug = "ashby"  # Ashby's own careers page
    company_label = "Ashby"
