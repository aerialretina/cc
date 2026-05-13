"""SmartRecruiters ATS spider — common in Canadian mid-market.

Public unauthenticated JSON API:

  GET https://api.smartrecruiters.com/v1/companies/{company_id}/postings

Returns ``{content: [{id, name, releasedDate, location, ...}], offset,
limit, totalFound}``. Same posting payload exposed to candidates on
the public job board; no rate-limit auth needed for read access.
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


class _SmartRecruitersBase(Spider):
    company_id: str = ""
    company_label: str = ""
    page_size: int = 100
    max_pages: int = 4

    def __init__(self) -> None:
        self._client = make_http_client(accept="application/json")

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
    def _fetch(self, offset: int) -> dict[str, Any]:
        url = f"https://api.smartrecruiters.com/v1/companies/{self.company_id}/postings"
        resp = self._client.get(url, params={"limit": self.page_size, "offset": offset})
        resp.raise_for_status()
        return resp.json()

    def crawl(self) -> Iterator[ScrapedPosting]:
        for page in range(self.max_pages):
            offset = page * self.page_size
            try:
                payload = self._fetch(offset)
            except (httpx.HTTPError, RetryError):
                logger.exception("smartrecruiters_fetch_failed",
                                 source=self.source_name, offset=offset)
                break
            postings = payload.get("content") or []
            if not postings:
                break
            for p in postings:
                yield _to_scraped(p, self.source_name, self.company_label or self.company_id)
            if len(postings) < self.page_size:
                break


def _to_scraped(p: dict[str, Any], source_name: str, company_label: str) -> ScrapedPosting:
    loc = p.get("location") or {}
    location_text = ", ".join(
        s for s in (loc.get("city"), loc.get("region"), loc.get("country"))
        if isinstance(s, str) and s
    )
    posted: date | None = None
    released = p.get("releasedDate") or p.get("createdOn")
    if isinstance(released, str):
        try:
            posted = dateparser.parse(released).date()
        except (ValueError, TypeError):
            posted = None
    return ScrapedPosting(
        source=source_name,
        source_posting_id=str(p.get("id") or p.get("refNumber", ""))[:255],
        source_url=(
            f"https://jobs.smartrecruiters.com/{p.get('company', {}).get('identifier','')}"
            f"/{p.get('id','')}" if isinstance(p.get("company"), dict) else ""
        ) or "",
        raw_title=p.get("name"),
        company_raw=company_label,
        location_raw=location_text or None,
        posted_date=posted,
        job_type=(p.get("typeOfEmployment") or {}).get("id") if isinstance(p.get("typeOfEmployment"), dict) else None,
        description_text=(p.get("jobAd") or {}).get("sections", {}).get("jobDescription", {}).get("text")
            if isinstance(p.get("jobAd"), dict) else None,
        raw_payload=str(p),
        extra={"sr_company_id": company_label, "department":
               (p.get("department") or {}).get("label") if isinstance(p.get("department"), dict) else None},
        scraped_at=datetime.now(UTC),
    )


# ---- concrete employers (mid-market on SmartRecruiters) ------------------

class BoschSmartRecruitersSpider(_SmartRecruitersBase):
    source_name = "smartrecruiters_bosch"
    description = "Bosch — SmartRecruiters ATS (Canada operations included)."
    tier = 1
    countries = ("CA", "US")
    homepage = "https://jobs.smartrecruiters.com/Bosch"
    company_id = "BoschGroup"
    company_label = "Bosch"


class IkeaSmartRecruitersSpider(_SmartRecruitersBase):
    source_name = "smartrecruiters_ikea"
    description = "IKEA — SmartRecruiters ATS."
    tier = 1
    countries = ("CA",)
    homepage = "https://jobs.smartrecruiters.com/IKEA"
    company_id = "IKEA"
    company_label = "IKEA"
