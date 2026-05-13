"""Adzuna aggregator API spider.

Adzuna indexes ~1M Canadian postings/month from employer career pages
and partner boards. Free tier: 1000 requests/month per account, 50
results per request. Sign up at https://developer.adzuna.com and set
LIP_ADZUNA_APP_ID + LIP_ADZUNA_APP_KEY on the Fly app.

API reference:
  GET https://api.adzuna.com/v1/api/jobs/ca/search/{page}
      ?app_id=...&app_key=...&what=...&where=...&results_per_page=50

This spider is the primary path to broad SMB and mid-market coverage —
the per-employer ATS spiders only reach large firms with their own
tenants. Adzuna pulls everything else.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import httpx
from dateutil import parser as dateparser
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from lip.config import get_settings
from lip.logging import get_logger
from lip.scraping.base import ScrapedPosting, Spider
from lip.scraping.http_client import make_http_client

logger = get_logger(__name__)

# Industrial-NOC-aligned search queries. Adzuna does free-text search;
# we use broad keywords because their indexer is good.
CA_QUERIES = (
    "construction project manager",
    "construction superintendent",
    "construction estimator",
    "civil engineer",
    "mechanical engineer",
    "electrical engineer",
    "process engineer",
    "pipeline engineer",
    "reservoir engineer",
    "completions engineer",
    "mine engineer",
    "geotechnical engineer",
    "millwright",
    "pipefitter",
    "welder red seal",
    "powerline technician",
    "heavy equipment operator",
    "industrial mechanic",
    "instrumentation technician",
    "boilermaker",
)


class _AdzunaBase(Spider):
    country_path: str = "ca"  # /ca = Canada
    page_size: int = 50

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = make_http_client(accept="application/json", timeout=20.0)

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._client.close()

    @property
    def _credentialled(self) -> bool:
        return bool(self._settings.adzuna_app_id and self._settings.adzuna_app_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
    def _fetch(self, query: str, page: int) -> dict[str, Any]:
        url = f"https://api.adzuna.com/v1/api/jobs/{self.country_path}/search/{page}"
        params = {
            "app_id": self._settings.adzuna_app_id,
            "app_key": self._settings.adzuna_app_key,
            "what": query,
            "results_per_page": self.page_size,
            "content-type": "application/json",
        }
        resp = self._client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def crawl(self) -> Iterator[ScrapedPosting]:
        if not self._credentialled:
            logger.warning("adzuna_no_credentials",
                           hint="Set LIP_ADZUNA_APP_ID and LIP_ADZUNA_APP_KEY")
            return

        for query in self._queries():
            try:
                payload = self._fetch(query, page=1)
            except (httpx.HTTPError, RetryError):
                logger.exception("adzuna_fetch_failed",
                                 source=self.source_name, query=query)
                continue
            for r in payload.get("results", []):
                yield _to_scraped(r, self.source_name)

    def _queries(self) -> tuple[str, ...]:
        return CA_QUERIES


def _to_scraped(r: dict[str, Any], source_name: str) -> ScrapedPosting:
    company = r.get("company") or {}
    company_name = company.get("display_name") if isinstance(company, dict) else None
    loc = r.get("location") or {}
    loc_text = loc.get("display_name") if isinstance(loc, dict) else None
    salary = None
    if r.get("salary_min") is not None or r.get("salary_max") is not None:
        salary = f"{r.get('salary_min') or '?'}-{r.get('salary_max') or '?'} {r.get('salary_is_predicted', '')}".strip()
    created = r.get("created")
    posted = None
    if isinstance(created, str):
        try:
            posted = dateparser.parse(created).date()
        except (ValueError, TypeError):
            posted = None
    return ScrapedPosting(
        source=source_name,
        source_posting_id=str(r.get("id", ""))[:255],
        source_url=r.get("redirect_url") or r.get("url") or "",
        raw_title=r.get("title"),
        company_raw=company_name,
        location_raw=loc_text,
        posted_date=posted,
        salary_raw=salary,
        job_type=r.get("contract_time"),
        description_text=r.get("description"),
        raw_payload=str(r),
        extra={
            "adzuna_category": (r.get("category") or {}).get("tag") if isinstance(r.get("category"), dict) else None,
            "adzuna_company_canonical": company.get("canonical_name") if isinstance(company, dict) else None,
        },
        scraped_at=datetime.now(UTC),
    )


class AdzunaCanadaSpider(_AdzunaBase):
    source_name = "adzuna_ca"
    description = "Adzuna Canada — aggregator covering SMB / mid-market / enterprise from 50+ board partners."
    tier = 3
    countries = ("CA",)
    homepage = "https://www.adzuna.ca"
    country_path = "ca"
