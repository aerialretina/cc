"""Vertical / niche job boards — Tier 2 sources from §1.1 of the plan.

Each spider here targets a specific industrial board. URL patterns and
parser shapes are committed; status is "scaffolded" until validated
end-to-end (most of these will likely require partner credentials or
proxy egress that's set up later).
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
from lip.scraping.sources.randstad import _parse as parse_jobposting_ldjson

logger = get_logger(__name__)


class _GenericLdJsonSpider(Spider):
    """Spider for any board that emits schema.org JobPosting microdata."""

    base_url: str = ""
    keywords: tuple[str, ...] = ()

    def __init__(self) -> None:
        self._client = make_http_client(accept="text/html")

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
    def _fetch(self, q: str) -> str:
        r = self._client.get(self.base_url, params={"q": q})
        r.raise_for_status()
        return r.text

    def crawl(self) -> Iterator[ScrapedPosting]:
        for kw in self.keywords or ("",):
            try:
                payload = self._fetch(kw)
            except (httpx.HTTPError, RetryError):
                logger.exception("vertical_board_fetch_failed", source=self.source_name, kw=kw)
                continue
            yield from parse_jobposting_ldjson(
                payload, source_name=self.source_name,
                base_url=self.base_url, scraped_at=datetime.now(UTC),
            )


class ConstructionJobsCanadaSpider(_GenericLdJsonSpider):
    source_name = "constructionjobs_ca"
    description = "ConstructionJobs.ca — Canadian construction-only board."
    tier = 2
    countries = ("CA",)
    homepage = "https://www.constructionjobs.com/canada"
    base_url = "https://www.constructionjobs.com/canada/jobs"
    keywords = ("project manager", "superintendent", "estimator")


class ConstructionJobSiteCASpider(_GenericLdJsonSpider):
    source_name = "constructionjobsite_ca"
    description = "ConstructionJobSite.ca — Annex Business Media (Canadian)."
    tier = 2
    countries = ("CA",)
    homepage = "https://www.constructionjobsite.ca"
    base_url = "https://www.constructionjobsite.ca/jobs"
    keywords = ("project manager", "estimator", "superintendent")


class EnergyJobShopSpider(_GenericLdJsonSpider):
    source_name = "energyjobshop"
    description = "EnergyJobShop.com — oil, gas, and pipelines."
    tier = 2
    countries = ("CA", "US")
    homepage = "https://www.energyjobshop.com"
    base_url = "https://www.energyjobshop.com/jobs"
    keywords = ("pipeline", "completions", "reservoir", "process")


class OilAndGasJobSearchSpider(_GenericLdJsonSpider):
    source_name = "oilandgas_jobsearch"
    description = "OilAndGasJobSearch.com — North American oil and gas roles."
    tier = 2
    countries = ("CA", "US")
    homepage = "https://www.oilandgasjobsearch.com"
    base_url = "https://www.oilandgasjobsearch.com/jobs"


class SPEJobBoardSpider(_GenericLdJsonSpider):
    source_name = "spe_jobboard"
    description = "Society of Petroleum Engineers job board."
    tier = 2
    countries = ("CA", "US")
    homepage = "https://www.spe.org/careers"
    base_url = "https://careers.spe.org/jobs"


class IndeedCanadaSpider(_GenericLdJsonSpider):
    """Indeed CA via Google for Jobs structured-data feed.

    Direct Indeed scraping is restricted; we read the schema.org
    JobPosting markup that Indeed emits on its public job-search pages,
    same format Google for Jobs reads. Lightweight — does not log in
    or solve captchas.
    """
    source_name = "indeed_ca"
    description = "Indeed Canada — structured JobPosting markup only."
    tier = 3
    countries = ("CA",)
    homepage = "https://ca.indeed.com"
    base_url = "https://ca.indeed.com/jobs"
    keywords = (
        "project manager construction",
        "superintendent",
        "completions engineer",
        "process engineer",
        "pipefitter",
    )


class IHireConstructionSpider(_GenericLdJsonSpider):
    source_name = "ihireconstruction"
    description = "iHireConstruction — US construction-only board."
    tier = 2
    countries = ("US",)
    homepage = "https://www.ihireconstruction.com"
    base_url = "https://www.ihireconstruction.com/jobs"
