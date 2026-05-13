"""Organization entity resolution (§2.4).

Matching order:
    exact canonical_name → exact alias → fuzzy on (name + aliases)
        with rapidfuzz token-set ratio above threshold.

For new strings that don't match anything, a placeholder Organization row
is created (canonical_name = the normalized form). Manual reconciliation
of placeholders runs as part of QA per §6.1.
"""

from __future__ import annotations

from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.orm import Session

from lip.enrichment.normalize import normalize_company
from lip.models import Organization

FUZZY_THRESHOLD = 88


def resolve_organization(db: Session, raw_name: str | None) -> Organization | None:
    if not raw_name:
        return None
    normalized = normalize_company(raw_name)
    if not normalized:
        return None

    exact = db.scalars(
        select(Organization).where(Organization.canonical_name == normalized).limit(1)
    ).first()
    if exact is not None:
        return exact

    alias_hit = db.scalars(
        select(Organization).where(Organization.aliases.contains([normalized])).limit(1)
    ).first()
    if alias_hit is not None:
        return alias_hit

    # Fuzzy match against an in-memory snapshot. Acceptable up to ~50k orgs;
    # beyond that, swap to a trigram GIN index + LIKE search.
    rows = db.scalars(select(Organization)).all()
    if not rows:
        return _create_placeholder(db, normalized, raw_name)

    choices = {org.id: org.canonical_name for org in rows}
    best = process.extractOne(
        normalized, choices, scorer=fuzz.token_set_ratio, score_cutoff=FUZZY_THRESHOLD
    )
    if best is None:
        return _create_placeholder(db, normalized, raw_name)

    matched_id = best[2]
    matched = next(o for o in rows if o.id == matched_id)
    if normalized not in matched.aliases:
        matched.aliases = [*matched.aliases, normalized]
    return matched


def _create_placeholder(db: Session, normalized: str, raw_name: str) -> Organization:
    org = Organization(canonical_name=normalized, aliases=[raw_name])
    db.add(org)
    db.flush()
    return org
