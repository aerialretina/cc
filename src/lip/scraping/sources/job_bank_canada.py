"""Job Bank Canada spider.

Job Bank publishes a JobSearch API (https://www.jobbank.gc.ca) and a
structured XML feed via its open data portal. Postings are NOC-tagged,
which makes this the lowest-risk, highest-structural-fit first source
(§1.1 Tier 2).

This spider hits the public JobSearch endpoint, filters for industrial
NOCs (construction, energy, skilled trades), and emits ``ScrapedPosting``
records. It uses the documented query parameters; no auth required.

For production, register for a Job Bank API user id (see ``LIP_JOB_BANK_USER_ID``)
and switch to the partner API which has richer fields and higher rate limits.
"""

from __future__ import annotations

import contextlib
import json
from collections.abc import Iterator
from datetime import date, datetime
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from lip.config import get_settings
from lip.logging import get_logger
from lip.scraping.base import ScrapedPosting, Spider

logger = get_logger(__name__)

# Industrial NOC seeds — expand as the taxonomy evolves.
# 72xxx: Industrial / construction / equipment trades.
# 73xxx: Heavy equipment / transport trades.
# 74xxx: Other installers, repairers, servicers.
# 95xxx: Labourers in processing, manufacturing and utilities.
# 22301: Civil engineering technologists / technicians (sample 2-digit seed).
INDUSTRIAL_NOC_PREFIXES: tuple[str, ...] = ("72", "73", "74", "95", "22")

BASE_URL = "https://www.jobbank.gc.ca/jobsearch/jobsearch"


class JobBankCanadaSpider(Spider):
    source_name = "job_bank_canada"
    crawl_frequency_hours = 12
    requires_browser = False

    def __init__(self, *, page_size: int = 25, max_pages: int = 40) -> None:
        self.page_size = page_size
        self.max_pages = max_pages
        self._settings = get_settings()
        self._client = httpx.Client(
            timeout=30.0,
            headers={
                "User-Agent": self._settings.scrape_user_agent,
                "Accept": "application/json, text/html;q=0.9",
            },
            follow_redirects=True,
        )

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
    def _fetch_page(self, prefix: str, page: int) -> dict[str, Any]:
        params = {
            "fnoc": prefix,
            "sort": "M",
            "fage": "7",
            "page": page,
            "fglf": "",
            "fsoc": "",
            "mid": page * self.page_size,
        }
        if self._settings.job_bank_user_id:
            params["userid"] = self._settings.job_bank_user_id
        response = self._client.get(BASE_URL, params=params)
        response.raise_for_status()
        # Job Bank returns HTML by default; partner API returns JSON.
        # Try JSON first, fall back to a minimal HTML parse for the public form.
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"_html": response.text, "_url": str(response.url)}

    def crawl(self) -> Iterator[ScrapedPosting]:
        for prefix in INDUSTRIAL_NOC_PREFIXES:
            for page in range(1, self.max_pages + 1):
                try:
                    payload = self._fetch_page(prefix, page)
                except httpx.HTTPError:
                    logger.exception("job_bank_fetch_failed", noc_prefix=prefix, page=page)
                    break

                postings = _extract_postings(payload)
                if not postings:
                    break

                yield from postings


def _extract_postings(payload: dict[str, Any]) -> list[ScrapedPosting]:
    """Pull postings from either the partner JSON or the public HTML.

    Kept as a free function so it can be unit-tested without HTTP.
    """
    if "_html" in payload:
        # Public HTML response — minimal extraction so the pipeline still
        # produces canonical records pending partner API access.
        return _parse_html_page(payload["_html"], payload.get("_url", ""))

    out: list[ScrapedPosting] = []
    for raw in payload.get("Jobs", []) or payload.get("jobs", []) or []:
        out.append(_from_partner_record(raw))
    return out


def _from_partner_record(raw: dict[str, Any]) -> ScrapedPosting:
    posting_id = str(raw.get("jobId") or raw.get("JobId") or raw.get("id"))
    return ScrapedPosting(
        source="job_bank_canada",
        source_posting_id=posting_id,
        source_url=raw.get("url") or f"https://www.jobbank.gc.ca/jobsearch/jobposting/{posting_id}",
        raw_title=raw.get("title") or raw.get("jobTitle"),
        company_raw=raw.get("employerName") or raw.get("EmployerName"),
        location_raw=raw.get("location") or raw.get("Location"),
        posted_date=_parse_date(raw.get("postedDate") or raw.get("datePosted")),
        salary_raw=raw.get("salary") or raw.get("Salary"),
        job_type=raw.get("jobType") or raw.get("JobType"),
        description_text=raw.get("description"),
        raw_payload=json.dumps(raw, sort_keys=True, ensure_ascii=False),
        extra={
            "noc": raw.get("noc") or raw.get("NOC"),
            "province": raw.get("province") or raw.get("Province"),
        },
    )


def _parse_html_page(html: str, page_url: str) -> list[ScrapedPosting]:
    """Best-effort extraction from the public HTML listing page.

    Job Bank's listing page emits ``<article class="resultJobItem">`` blocks
    with predictable child elements. We avoid pulling in a heavy parser at
    the base layer — full extraction lands when ``beautifulsoup4`` is added
    via the ``scraping`` extra.
    """
    try:
        from bs4 import BeautifulSoup  # type: ignore[import-not-found]
    except ImportError:
        logger.warning("bs4_unavailable_falling_back_to_empty", url=page_url)
        return []

    soup = BeautifulSoup(html, "html.parser")
    postings: list[ScrapedPosting] = []
    for item in soup.select("article.resultJobItem, article.action-buttons"):
        href = item.find("a")
        if not href or not href.get("href"):
            continue
        url = httpx.URL(page_url).join(href["href"])
        posting_id = url.path.rsplit("/", 1)[-1]
        title_el = item.find(class_="noctitle") or item.find("h3")
        employer_el = item.find(class_="business")
        location_el = item.find(class_="location")
        salary_el = item.find(class_="salary")
        date_el = item.find("time")

        postings.append(
            ScrapedPosting(
                source="job_bank_canada",
                source_posting_id=posting_id,
                source_url=str(url),
                raw_title=_text(title_el),
                company_raw=_text(employer_el),
                location_raw=_text(location_el),
                posted_date=_parse_date(date_el.get("datetime") if date_el else None),
                salary_raw=_text(salary_el),
                raw_payload=str(item),
            )
        )
    return postings


def _text(el) -> str | None:  # type: ignore[no-untyped-def]
    if el is None:
        return None
    text = el.get_text(strip=True)
    return text or None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value[: len(fmt)], fmt).date()
        except ValueError:
            continue
    return None
