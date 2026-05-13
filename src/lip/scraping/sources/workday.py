"""Workday ATS spider — covers many large Canadian employers.

Workday exposes a stable JSON search endpoint per tenant:

  POST https://{tenant}.{cluster}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
  body: {"appliedFacets":{},"limit":20,"offset":0,"searchText":""}

The response includes ``jobPostings`` with title, locationsText,
externalPath, postedOn, and bulletFields. No auth, no bot challenge —
Workday's career sites are designed to be machine-readable for
syndication.

Add a new employer by subclassing and setting ``tenant``, ``cluster``,
``site``, and ``source_name``.
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


class _WorkdayBase(Spider):
    tenant: str = ""
    cluster: str = "wd3"  # wd1 / wd3 / wd5 — depends on the tenant
    site: str = "External"  # career-site slug within the tenant
    page_size: int = 50
    max_pages: int = 4
    company_label: str = ""  # human-readable for ScrapedPosting.company_raw

    def __init__(self) -> None:
        self._client = make_http_client(accept="application/json")

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._client.close()

    @property
    def endpoint(self) -> str:
        return (
            f"https://{self.tenant}.{self.cluster}.myworkdayjobs.com/wday/cxs/"
            f"{self.tenant}/{self.site}/jobs"
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
    def _fetch_page(self, offset: int) -> dict[str, Any]:
        body = {"appliedFacets": {}, "limit": self.page_size, "offset": offset, "searchText": ""}
        resp = self._client.post(self.endpoint, json=body)
        resp.raise_for_status()
        return resp.json()

    def crawl(self) -> Iterator[ScrapedPosting]:
        for page in range(self.max_pages):
            offset = page * self.page_size
            try:
                payload = self._fetch_page(offset)
            except (httpx.HTTPError, RetryError):
                logger.exception("workday_fetch_failed",
                                 source=self.source_name, offset=offset)
                break
            postings = payload.get("jobPostings") or []
            if not postings:
                break
            for p in postings:
                ext_path = p.get("externalPath") or ""
                source_url = (
                    f"https://{self.tenant}.{self.cluster}.myworkdayjobs.com"
                    f"/en-US/{self.site}{ext_path}"
                )
                posted_on = _parse_posted(p.get("postedOn"))
                yield ScrapedPosting(
                    source=self.source_name,
                    source_posting_id=str(p.get("bulletFields", [None])[0]
                                          or ext_path or p.get("title", ""))[:255],
                    source_url=source_url,
                    raw_title=p.get("title"),
                    company_raw=self.company_label or self.tenant,
                    location_raw=p.get("locationsText"),
                    posted_date=posted_on,
                    description_text=None,
                    raw_payload=str(p),
                    extra={"workday_tenant": self.tenant, "workday_site": self.site},
                    scraped_at=datetime.now(UTC),
                )


def _parse_posted(label: str | None) -> date | None:
    """Workday returns relative strings like 'Posted 3 Days Ago'."""
    if not label or not isinstance(label, str):
        return None
    import re
    m = re.search(r"Posted\s+(\d+)\+?\s+(Day|Week|Month)s?\s+Ago", label, re.I)
    if not m:
        if "today" in label.lower():
            return date.today()
        return None
    n = int(m.group(1))
    unit = m.group(2).lower()
    days = n * {"day": 1, "week": 7, "month": 30}.get(unit, 1)
    from datetime import timedelta
    return date.today() - timedelta(days=days)


# ---------------------------------------------------------------------------
# Concrete employer spiders. Tenants / sites verified against each company's
# public careers page. If a tenant URL changes, override here.
# ---------------------------------------------------------------------------

class PCLWorkdaySpider(_WorkdayBase):
    source_name = "workday_pcl"
    description = "PCL Construction — Workday ATS."
    tier = 1
    countries = ("CA", "US")
    homepage = "https://www.pcl.com/careers"
    tenant = "pcl"
    cluster = "wd1"
    site = "External"
    company_label = "PCL Construction Group"


class OPGWorkdaySpider(_WorkdayBase):
    source_name = "workday_opg"
    description = "Ontario Power Generation — Workday ATS."
    tier = 1
    countries = ("CA",)
    homepage = "https://jobs.opg.com"
    tenant = "opg"
    cluster = "wd3"
    site = "External"
    company_label = "Ontario Power Generation"


class SuncorWorkdaySpider(_WorkdayBase):
    source_name = "workday_suncor"
    description = "Suncor Energy — Workday ATS."
    tier = 1
    countries = ("CA",)
    homepage = "https://jobs.suncor.com"
    tenant = "suncor"
    cluster = "wd3"
    site = "Careers"
    company_label = "Suncor Energy"


class CamecoWorkdaySpider(_WorkdayBase):
    source_name = "workday_cameco"
    description = "Cameco Corporation — Workday ATS."
    tier = 1
    countries = ("CA",)
    homepage = "https://www.cameco.com/careers"
    tenant = "cameco"
    cluster = "wd3"
    site = "External"
    company_label = "Cameco Corporation"


class EnbridgeWorkdaySpider(_WorkdayBase):
    source_name = "workday_enbridge"
    description = "Enbridge — Workday ATS."
    tier = 1
    countries = ("CA", "US")
    homepage = "https://careers.enbridge.com"
    tenant = "enbridge"
    cluster = "wd3"
    site = "External"
    company_label = "Enbridge"


class AtkinsRealisWorkdaySpider(_WorkdayBase):
    source_name = "workday_atkinsrealis"
    description = "AtkinsRéalis (formerly SNC-Lavalin) — Workday ATS."
    tier = 1
    countries = ("CA",)
    homepage = "https://www.atkinsrealis.com/en/careers"
    tenant = "atkinsrealis"
    cluster = "wd3"
    site = "External"
    company_label = "AtkinsRéalis"


class TeckWorkdaySpider(_WorkdayBase):
    source_name = "workday_teck"
    description = "Teck Resources — Workday ATS."
    tier = 1
    countries = ("CA",)
    homepage = "https://www.teck.com/careers"
    tenant = "teck"
    cluster = "wd3"
    site = "External"
    company_label = "Teck Resources"


class HydroOneWorkdaySpider(_WorkdayBase):
    source_name = "workday_hydroone"
    description = "Hydro One — Workday ATS."
    tier = 1
    countries = ("CA",)
    homepage = "https://www.hydroone.com/careers"
    tenant = "hydroone"
    cluster = "wd3"
    site = "External"
    company_label = "Hydro One"
