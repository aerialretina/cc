"""End-to-end enrichment for a single RawPosting.

Resolves a RawPosting into a canonical Posting through the three-step
dedup pipeline (§1.3) and the §2 enrichment modules.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from lip.db import session_scope
from lip.enrichment import compensation, dedup, entity_resolution, location, occupation, skills
from lip.logging import get_logger
from lip.models import Posting, RawPosting

logger = get_logger(__name__)


def enrich(source: str, source_posting_id: str) -> Posting | None:
    """Promote a RawPosting to (or merge into) a canonical Posting."""
    with session_scope() as db:
        raw = (
            db.query(RawPosting)
            .filter(
                RawPosting.source == source,
                RawPosting.source_posting_id == source_posting_id,
            )
            .one_or_none()
        )
        if raw is None:
            logger.warning("enrich_raw_missing", source=source, sid=source_posting_id)
            return None

        return _enrich_in_session(db, raw)


def _enrich_in_session(db: Session, raw: RawPosting) -> Posting:
    key = dedup.compute_dedup_key(raw)

    # Step 2 — cross-source normalized match.
    existing = dedup.find_matching_canonical(db, key)

    # Enrichment fields.
    occ = occupation.classify(raw.raw_title, raw.description_text)
    extracted_skills = skills.extract(raw.description_text)
    comp = compensation.extract(raw.salary_raw or raw.description_text)
    org = entity_resolution.resolve_organization(db, raw.company_raw)
    loc = location.resolve(raw.location_raw)

    now = datetime.now(UTC)

    if existing is None:
        posting = Posting(
            organization_id=org.id if org else None,
            title=raw.raw_title or "(untitled)",
            occupation_code=occ.occupation_code,
            occupation_system=occ.occupation_system,
            industrial_overlay_code=occ.industrial_overlay_code,
            seniority=occ.seniority,
            region_code=loc.region_code if loc else None,
            location_text=loc.location_text if loc else raw.location_raw,
            latitude=loc.latitude if loc else None,
            longitude=loc.longitude if loc else None,
            salary_low=Decimal(comp.amount_low) if comp and comp.amount_low else None,
            salary_high=Decimal(comp.amount_high) if comp and comp.amount_high else None,
            salary_currency=comp.currency if comp else None,
            salary_period=comp.period if comp else None,
            skills=extracted_skills.skills,
            certifications=extracted_skills.certifications,
            first_seen_at=raw.scraped_at or now,
            last_seen_at=raw.scraped_at or now,
            is_active=True,
            source_count=1,
            dedup_key=key.hash(),
            confidence={"occupation": occ.confidence},
        )
        db.add(posting)
        db.flush()
    else:
        posting = existing
        posting.last_seen_at = raw.scraped_at or now
        posting.source_count = (posting.source_count or 0) + 1
        if posting.skills != extracted_skills.skills:
            posting.skills = sorted(set([*posting.skills, *extracted_skills.skills]))
        if posting.certifications != extracted_skills.certifications:
            posting.certifications = sorted(
                set([*posting.certifications, *extracted_skills.certifications])
            )
        if not posting.organization_id and org is not None:
            posting.organization_id = org.id

    raw.posting_id = posting.id
    return posting
