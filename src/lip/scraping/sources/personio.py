"""Personio ATS spider.

Personio is European-origin but used by a growing slice of mid-market
firms with Canadian operations. Public XML job-feed endpoint per
tenant:

  GET https://{slug}.jobs.personio.com/xml

Returns RSS-like XML with positions, recruitingCategory, department,
office, schedule. Skipped silently if XML parsing fails.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from datetime import UTC, datetime
from xml.etree import ElementTree as ET

import httpx
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from lip.logging import get_logger
from lip.scraping.base import ScrapedPosting, Spider
from lip.scraping.http_client import make_http_client

logger = get_logger(__name__)


class _PersonioBase(Spider):
    slug: str = ""
    company_label: str = ""

    def __init__(self) -> None:
        self._client = make_http_client(accept="application/xml, text/xml")

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
    def _fetch(self) -> str:
        url = f"https://{self.slug}.jobs.personio.com/xml"
        resp = self._client.get(url)
        resp.raise_for_status()
        return resp.text

    def crawl(self) -> Iterator[ScrapedPosting]:
        try:
            xml = self._fetch()
        except (httpx.HTTPError, RetryError):
            logger.exception("personio_fetch_failed", source=self.source_name)
            return
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            logger.exception("personio_xml_parse_failed", source=self.source_name)
            return
        for pos in root.findall(".//position"):
            yield ScrapedPosting(
                source=self.source_name,
                source_posting_id=str(_text(pos, "id"))[:255],
                source_url=_text(pos, "url") or "",
                raw_title=_text(pos, "name"),
                company_raw=self.company_label or self.slug,
                location_raw=_text(pos, "office"),
                job_type=_text(pos, "schedule"),
                description_text=_text(pos, "jobDescriptions"),
                raw_payload=ET.tostring(pos, encoding="unicode"),
                extra={"personio_slug": self.slug,
                       "department": _text(pos, "department"),
                       "category": _text(pos, "recruitingCategory")},
                scraped_at=datetime.now(UTC),
            )


def _text(elem: ET.Element, tag: str) -> str | None:
    child = elem.find(tag)
    return (child.text or "").strip() if child is not None and child.text else None


class PersonioExampleSpider(_PersonioBase):
    """Placeholder; swap `slug` to a real Personio-using firm with CA ops."""
    source_name = "personio_example"
    description = "Personio ATS — replace `slug` with a real employer."
    tier = 1
    countries = ("CA",)
    homepage = "https://www.personio.com"
    slug = "personio"
    company_label = "Personio"
