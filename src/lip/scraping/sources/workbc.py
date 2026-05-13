"""WorkBC spider — British Columbia provincial job board.

WorkBC's job-search API returns JSON. NOC-tagged and well-suited for
LNG, mining, and forestry industrial postings.
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


class WorkBCSpider(Spider):
    source_name = "workbc"
    description = "WorkBC — British Columbia provincial job board, NOC-tagged."
    tier = 3
    countries = ("CA",)
    homepage = "https://www.workbc.ca"
    base_url = "https://www.workbc.ca/api/job-board/search"

    NOC_FILTERS = ("70010", "72014", "21300", "21301", "21331", "72301", "72106", "73400")

    def __init__(self) -> None:
        self._client = make_http_client(accept="application/json")

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
    def _fetch(self, noc: str) -> dict:
        r = self._client.get(self.base_url, params={"noc": noc, "page": 1})
        r.raise_for_status()
        return r.json()

    def crawl(self) -> Iterator[ScrapedPosting]:
        for noc in self.NOC_FILTERS:
            try:
                payload = self._fetch(noc)
            except (httpx.HTTPError, RetryError, ValueError):
                logger.exception("workbc_fetch_failed", noc=noc)
                continue
            for j in payload.get("jobs", []):
                yield ScrapedPosting(
                    source=self.source_name,
                    source_posting_id=str(j.get("id") or j.get("jobId", ""))[:255],
                    source_url=j.get("url") or self.base_url,
                    raw_title=j.get("title"),
                    company_raw=j.get("employer"),
                    location_raw=j.get("location"),
                    salary_raw=j.get("salary"),
                    job_type=j.get("jobType"),
                    description_text=j.get("description"),
                    raw_payload=str(j),
                    extra={"noc_filter": noc},
                    scraped_at=datetime.now(UTC),
                )
