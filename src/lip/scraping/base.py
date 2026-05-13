"""Base spider abstraction.

Each source is a subclass that yields ``ScrapedPosting`` objects. The base
class does not depend on Scrapy directly so spiders can be implemented with
plain ``httpx`` for API sources or Scrapy+Playwright for HTML sources.
"""

from __future__ import annotations

import abc
import hashlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any


@dataclass(slots=True)
class ScrapedPosting:
    """A single record emitted by a spider — to be persisted as RawPosting."""

    source: str
    source_posting_id: str
    source_url: str
    raw_title: str | None = None
    company_raw: str | None = None
    location_raw: str | None = None
    posted_date: date | None = None
    salary_raw: str | None = None
    job_type: str | None = None
    description_text: str | None = None
    raw_payload: str = ""  # canonical raw form (HTML or JSON) used for hashing
    extra: dict[str, Any] = field(default_factory=dict)
    scraped_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def html_hash(self) -> str:
        return hashlib.sha256(self.raw_payload.encode("utf-8")).hexdigest()


class Spider(abc.ABC):
    """Abstract spider.

    Subclasses must set ``source_name`` and implement ``crawl()``. The
    metadata fields (tier, country, description, ...) drive the
    ``/ui/sources`` coverage page and the registered-spiders count.
    """

    source_name: str
    description: str = ""
    # 1 = direct company career pages, 2 = vertical / niche boards,
    # 3 = general boards (Indeed, LinkedIn), 4 = associations / aggregators.
    tier: int = 3
    countries: tuple[str, ...] = ()  # ISO-3166-1 alpha-2, e.g. ("CA",) or ("CA","US","UK")
    crawl_frequency_hours: int = 24
    requires_browser: bool = False
    # "live" once the spider has been validated end-to-end; "scaffolded"
    # while only the URL pattern + parser shape are committed.
    status: str = "scaffolded"
    homepage: str = ""

    @abc.abstractmethod
    def crawl(self) -> Iterator[ScrapedPosting]:
        """Yield postings discovered in a single crawl run."""
        raise NotImplementedError

    @classmethod
    def is_configured(cls) -> bool:
        """Whether the spider has the prerequisite secrets it needs to run.

        Default True — most spiders have no required config. Override on
        any spider that depends on an API key or partner credential
        (e.g. Adzuna requires LIP_ADZUNA_APP_ID + LIP_ADZUNA_APP_KEY).
        Drives the "config missing" pill on /ui/sources.
        """
        return True
