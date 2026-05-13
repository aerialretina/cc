"""Lever ATS spider.

Public, unauthenticated JSON API:

  GET https://api.lever.co/v0/postings/{company}?mode=json

Returns an array of postings with ``id``, ``text``, ``categories``
(team, location, commitment), ``description``, ``hostedUrl``,
``createdAt`` (millis since epoch).
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from datetime import UTC, date, datetime
from typing import Any

import httpx
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from lip.logging import get_logger
from lip.scraping.base import ScrapedPosting, Spider
from lip.scraping.http_client import make_http_client

logger = get_logger(__name__)


class _LeverBase(Spider):
    company_slug: str = ""
    company_label: str = ""

    def __init__(self) -> None:
        self._client = make_http_client(accept="application/json")

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._client.close()

    @property
    def endpoint(self) -> str:
        return f"https://api.lever.co/v0/postings/{self.company_slug}?mode=json"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
    def _fetch(self) -> list[Any]:
        resp = self._client.get(self.endpoint)
        resp.raise_for_status()
        return resp.json()

    def crawl(self) -> Iterator[ScrapedPosting]:
        try:
            postings = self._fetch()
        except (httpx.HTTPError, RetryError):
            logger.exception("lever_fetch_failed", source=self.source_name)
            return
        for p in postings:
            if not isinstance(p, dict):
                continue
            cats = p.get("categories", {}) or {}
            created_ms = p.get("createdAt")
            posted = (
                date.fromtimestamp(created_ms / 1000)
                if isinstance(created_ms, (int, float)) and created_ms > 0
                else None
            )
            yield ScrapedPosting(
                source=self.source_name,
                source_posting_id=str(p.get("id", ""))[:255],
                source_url=p.get("hostedUrl") or self.endpoint,
                raw_title=p.get("text"),
                company_raw=self.company_label or self.company_slug,
                location_raw=cats.get("location"),
                posted_date=posted,
                job_type=cats.get("commitment"),
                description_text=p.get("descriptionPlain") or p.get("description"),
                raw_payload=str(p),
                extra={"lever_slug": self.company_slug, "team": cats.get("team")},
                scraped_at=datetime.now(UTC),
            )


# Concrete subclasses kept minimal — Lever is more common at scale-ups.
# Adding stubs for two known users gives the registry surface area;
# easy to extend.

class ChandosLeverSpider(_LeverBase):
    source_name = "lever_chandos"
    description = "Chandos Construction — Lever ATS (if active)."
    tier = 1
    countries = ("CA",)
    homepage = "https://chandos.com/careers"
    company_slug = "chandos"
    company_label = "Chandos Construction"
