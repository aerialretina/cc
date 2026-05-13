"""Compensation extraction from posting text (§2.3).

Estimation (the comp model trained on placement-verified ground truth +
extracted salary + government wages) is implemented under
``lip.enrichment.compensation_model`` once enough placement data exists.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# The en-dash in the range separator is intentional - postings commonly use
# the typographic form "120<en-dash>150" rather than the ASCII "120-150".
_RANGE_SEPARATOR = "[\\-–to]+"  # ASCII hyphen, en-dash (U+2013), or "to"

_RANGE_RE = re.compile(
    r"""
    (?P<currency>\$|CAD|USD|US\$|C\$)?\s*
    (?P<low>\d{1,3}(?:,\d{3})*(?:\.\d+)?)
    \s*[kK]?\s*
    (?:""" + _RANGE_SEPARATOR + r""")\s*
    (?P<currency2>\$|CAD|USD|US\$|C\$)?\s*
    (?P<high>\d{1,3}(?:,\d{3})*(?:\.\d+)?)
    \s*(?P<k>[kK])?\s*
    (?P<period>per\s+(?:hour|year|annum)|/(?:hr|yr|year|hour)|annually|hourly)?
    """,
    re.IGNORECASE | re.VERBOSE,
)


@dataclass(slots=True)
class ExtractedCompensation:
    amount_low: float | None
    amount_high: float | None
    currency: str | None
    period: str  # "annual" | "hourly"


def extract(text: str | None) -> ExtractedCompensation | None:
    if not text:
        return None

    match = _RANGE_RE.search(text)
    if match is None:
        return None

    low = _to_number(match.group("low"))
    high = _to_number(match.group("high"))
    if low is None or high is None:
        return None

    k_multiplier = 1000 if match.group("k") else 1
    period_raw = (match.group("period") or "").lower()
    if "hour" in period_raw or "hr" in period_raw:
        period = "hourly"
    elif "year" in period_raw or "annum" in period_raw or "annually" in period_raw:
        period = "annual"
    else:
        # If values look like hourly wages (small), call it hourly; else annual.
        period = "hourly" if max(low, high) * k_multiplier < 200 else "annual"

    low_v = low * k_multiplier
    high_v = high * k_multiplier
    if low_v > high_v:
        low_v, high_v = high_v, low_v

    currency_token = (match.group("currency") or match.group("currency2") or "").upper()
    currency = _currency_code(currency_token)

    return ExtractedCompensation(
        amount_low=low_v,
        amount_high=high_v,
        currency=currency,
        period=period,
    )


def _to_number(s: str | None) -> float | None:
    if s is None:
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def _currency_code(token: str) -> str | None:
    if token in {"$", "USD", "US$"}:
        return "USD"
    if token in {"CAD", "C$"}:
        return "CAD"
    return None
