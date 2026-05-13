"""GET /v1/postings — search and filter canonical (deduplicated) postings."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from lip.api.schemas import PostingOut
from lip.db import get_db
from lip.models import Posting

router = APIRouter()


@router.get("", response_model=list[PostingOut])
def list_postings(
    db: Session = Depends(get_db),
    sector: str | None = Query(default=None),
    region_code: str | None = Query(default=None, description="ISO-3166-2 (e.g. CA-AB, US-TX)"),
    occupation_code: str | None = Query(default=None),
    occupation_system: str | None = Query(default=None, description="NOC or SOC"),
    industrial_overlay_code: str | None = Query(default=None),
    skill: list[str] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    active_only: bool = Query(default=True),
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Posting]:
    stmt = select(Posting)

    if active_only:
        stmt = stmt.where(Posting.is_active.is_(True))
    if region_code:
        stmt = stmt.where(Posting.region_code == region_code)
    if occupation_code:
        stmt = stmt.where(Posting.occupation_code == occupation_code)
    if occupation_system:
        stmt = stmt.where(Posting.occupation_system == occupation_system)
    if industrial_overlay_code:
        stmt = stmt.where(Posting.industrial_overlay_code == industrial_overlay_code)
    if skill:
        stmt = stmt.where(Posting.skills.contains(skill))
    if date_from:
        stmt = stmt.where(Posting.first_seen_at >= date_from)
    if date_to:
        stmt = stmt.where(Posting.last_seen_at <= date_to)
    if sector:
        # Sector filter currently routes through organization.sector_tags;
        # joined filter implemented when organization registry is populated.
        from lip.models import Organization
        stmt = stmt.join(Organization, isouter=True).where(
            Organization.sector_tags.contains([sector])
        )

    stmt = stmt.order_by(Posting.last_seen_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())
