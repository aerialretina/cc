"""Spider registry — map source_name → spider class."""

from __future__ import annotations

from lip.scraping.base import Spider
from lip.scraping.sources.job_bank_canada import JobBankCanadaSpider

_REGISTRY: dict[str, type[Spider]] = {
    JobBankCanadaSpider.source_name: JobBankCanadaSpider,
}


def get_spider(source_name: str) -> type[Spider]:
    try:
        return _REGISTRY[source_name]
    except KeyError as exc:
        raise KeyError(f"unknown spider: {source_name}") from exc


def list_spiders() -> list[str]:
    return sorted(_REGISTRY.keys())
