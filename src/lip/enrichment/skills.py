"""Skill + certification extraction (§2.2).

The production approach is a fine-tuned BERT span-NER. This module exposes
the interface the pipeline depends on and ships with a deterministic
keyword + regex fallback so the pipeline produces real outputs from day one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from lip.taxonomy.skills import CERTIFICATIONS, SOFTWARE_SKILLS, TECHNICAL_SKILLS


@dataclass(slots=True)
class ExtractedSkills:
    skills: list[str]
    certifications: list[str]


def extract(description: str | None) -> ExtractedSkills:
    if not description:
        return ExtractedSkills(skills=[], certifications=[])

    matched_skills: list[str] = []
    for canonical, aliases in (*TECHNICAL_SKILLS.items(), *SOFTWARE_SKILLS.items()):
        for alias in (canonical, *aliases):
            if _phrase_present(alias, description):
                matched_skills.append(canonical)
                break

    matched_certs: list[str] = []
    for cert, aliases in CERTIFICATIONS.items():
        for alias in (cert, *aliases):
            if _phrase_present(alias, description):
                matched_certs.append(cert)
                break

    return ExtractedSkills(
        skills=sorted(set(matched_skills)),
        certifications=sorted(set(matched_certs)),
    )


def _phrase_present(phrase: str, text: str) -> bool:
    """Word-boundary phrase match, ignoring case.

    A phrase like "Primavera P6" matches "primavera p6." but not
    "primavera p60". Punctuation in the source text doesn't block the match.
    """
    pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"
    return re.search(pattern, text, re.IGNORECASE) is not None
