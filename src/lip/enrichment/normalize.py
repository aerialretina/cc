"""Field normalization used by the dedup key (§1.3 Step 2)."""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^a-z0-9 ]+")
_TITLE_SUFFIXES = re.compile(
    r"\b(jr\.?|sr\.?|i{1,3}|iv|v|vi{1,3}|ix|x)\b",
    flags=re.IGNORECASE,
)
_COMPANY_SUFFIXES = re.compile(
    r"\b("
    r"inc\.?|incorporated|corp\.?|corporation|ltd\.?|limited|llc|llp|lp|"
    r"co\.?|company|gmbh|s\.?a\.?|plc|holdings?|group|services?"
    r")\b",
    flags=re.IGNORECASE,
)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    nfkd = unicodedata.normalize("NFKD", value)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii").lower()
    return _WHITESPACE.sub(" ", _NON_ALNUM.sub(" ", ascii_str)).strip()


def normalize_title(title: str | None) -> str:
    """Strip seniority Roman numerals and common suffixes; lowercase."""
    if not title:
        return ""
    cleaned = _TITLE_SUFFIXES.sub("", title)
    return normalize_text(cleaned)


def normalize_company(name: str | None) -> str:
    """Strip legal-entity suffixes; lowercase."""
    if not name:
        return ""
    cleaned = _COMPANY_SUFFIXES.sub("", name)
    return normalize_text(cleaned)


def normalize_location(location: str | None) -> str:
    """Lowercase, strip punctuation; canonical form lands with geocoder."""
    return normalize_text(location)
