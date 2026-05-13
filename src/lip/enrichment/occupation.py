"""Occupation classification (§2.1).

Hybrid: NOC 2021 (Canada) and SOC 2018 (US) as the standard backbone, with
the proprietary industrial overlay layered on top.

The full classifier is trained on labeled placement-history data once
~2,000 examples exist. Until then, a rule-based fallback handles obvious
keyword matches so the rest of the pipeline can run end-to-end on real
data.
"""

from __future__ import annotations

from dataclasses import dataclass

from lip.enrichment.normalize import normalize_title
from lip.taxonomy.industrial import INDUSTRIAL_OVERLAY


@dataclass(slots=True)
class OccupationLabel:
    occupation_system: str | None  # "NOC" | "SOC"
    occupation_code: str | None
    industrial_overlay_code: str | None
    seniority: str | None
    confidence: float


_SENIORITY_KEYWORDS = (
    ("senior", "senior"),
    ("lead", "lead"),
    ("principal", "principal"),
    ("director", "director"),
    ("manager", "manager"),
    ("junior", "junior"),
    ("intermediate", "intermediate"),
    ("intern", "intern"),
    ("apprentice", "apprentice"),
    ("journeyperson", "journeyperson"),
    ("journeyman", "journeyperson"),
    ("foreman", "foreman"),
    ("superintendent", "superintendent"),
    ("executive", "executive"),
    ("chief", "chief"),
)


def classify(title: str | None, description: str | None = None) -> OccupationLabel:
    """Rule-based first pass; ML classifier swaps in when trained."""
    norm_title = normalize_title(title)
    text = f"{norm_title} {(description or '').lower()}"

    overlay_code: str | None = None
    best_score = 0
    for code, entry in INDUSTRIAL_OVERLAY.items():
        for kw in entry["keywords"]:
            if kw in text:
                score = len(kw)
                if score > best_score:
                    best_score = score
                    overlay_code = code

    seniority = None
    for kw, label in _SENIORITY_KEYWORDS:
        if kw in norm_title:
            seniority = label
            break

    return OccupationLabel(
        occupation_system=None,
        occupation_code=None,
        industrial_overlay_code=overlay_code,
        seniority=seniority,
        confidence=0.5 if overlay_code else 0.2,
    )
