"""Tier-1 company career-page spiders.

Per §1.1 these are the highest-signal sources — postings often appear
here days before they hit aggregators, and many never make it to the
general boards at all. Each subclass targets one company's career site.

Spiders are scaffolded with the right URL pattern; the parser uses the
schema.org JobPosting microdata that most modern ATS systems emit
(Workday, SmartRecruiters, Greenhouse, Lever, iCIMS).
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from datetime import UTC, datetime

import httpx
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from lip.config import get_settings
from lip.logging import get_logger
from lip.scraping.base import ScrapedPosting, Spider
from lip.scraping.sources.randstad import _parse as parse_jobposting_ldjson

logger = get_logger(__name__)


class _Tier1Base(Spider):
    base_url: str = ""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = httpx.Client(
            timeout=15.0,
            headers={"User-Agent": self._settings.scrape_user_agent},
            follow_redirects=True,
        )

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
    def _fetch(self) -> str:
        r = self._client.get(self.base_url)
        r.raise_for_status()
        return r.text

    def crawl(self) -> Iterator[ScrapedPosting]:
        try:
            payload = self._fetch()
        except (httpx.HTTPError, RetryError):
            logger.exception("tier1_fetch_failed", source=self.source_name)
            return
        yield from parse_jobposting_ldjson(
            payload, source_name=self.source_name,
            base_url=self.base_url, scraped_at=datetime.now(UTC),
        )


class PCLCareersSpider(_Tier1Base):
    source_name = "careers_pcl"
    description = "PCL Construction — direct careers page."
    tier = 1
    countries = ("CA", "US")
    crawl_frequency_hours = 24
    homepage = "https://www.pcl.com"
    base_url = "https://careers.pcl.com/jobs"


class AeconCareersSpider(_Tier1Base):
    source_name = "careers_aecon"
    description = "Aecon Group — direct careers page."
    tier = 1
    countries = ("CA",)
    homepage = "https://www.aecon.com"
    base_url = "https://careers.aecon.com/search"


class EllisDonCareersSpider(_Tier1Base):
    source_name = "careers_ellisdon"
    description = "EllisDon — direct careers page."
    tier = 1
    countries = ("CA",)
    homepage = "https://www.ellisdon.com"
    base_url = "https://careers.ellisdon.com/search/jobs"


class SuncorCareersSpider(_Tier1Base):
    source_name = "careers_suncor"
    description = "Suncor Energy — direct careers page."
    tier = 1
    countries = ("CA",)
    homepage = "https://www.suncor.com"
    base_url = "https://jobs.suncor.com/search/"


class TCEnergyCareersSpider(_Tier1Base):
    source_name = "careers_tcenergy"
    description = "TC Energy — direct careers page."
    tier = 1
    countries = ("CA", "US")
    homepage = "https://www.tcenergy.com"
    base_url = "https://careers.tcenergy.com/search/"


class EnbridgeCareersSpider(_Tier1Base):
    source_name = "careers_enbridge"
    description = "Enbridge — direct careers page."
    tier = 1
    countries = ("CA", "US")
    homepage = "https://www.enbridge.com"
    base_url = "https://careers.enbridge.com/jobs"


class OPGCareersSpider(_Tier1Base):
    source_name = "careers_opg"
    description = "Ontario Power Generation — direct careers page."
    tier = 1
    countries = ("CA",)
    homepage = "https://www.opg.com"
    base_url = "https://jobs.opg.com/search/"


class BrucePowerCareersSpider(_Tier1Base):
    source_name = "careers_bruce_power"
    description = "Bruce Power — direct careers page."
    tier = 1
    countries = ("CA",)
    homepage = "https://www.brucepower.com"
    base_url = "https://www.brucepower.com/careers/"
