"""GET /v1/organizations/* — organization registry and hiring activity."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lip.api.schemas import OrganizationOut, OrgHiringActivity
from lip.db import get_db
from lip.models import Organization, Posting

router = APIRouter()


@router.get("/{org_id}", response_model=OrganizationOut)
def get_organization(org_id: UUID, db: Session = Depends(get_db)) -> Organization:
    org = db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="organization not found")
    return org


@router.get("/{org_id}/hiring-activity", response_model=OrgHiringActivity)
def hiring_activity(
    org_id: UUID,
    db: Session = Depends(get_db),
    window_days: int = Query(default=90, ge=1, le=730),
) -> OrgHiringActivity:
    if db.get(Organization, org_id) is None:
        raise HTTPException(status_code=404, detail="organization not found")

    cutoff = datetime.now(UTC) - timedelta(days=window_days)

    active = db.scalar(
        select(func.count())
        .select_from(Posting)
        .where(Posting.organization_id == org_id, Posting.is_active.is_(True))
    ) or 0
    new = db.scalar(
        select(func.count())
        .select_from(Posting)
        .where(Posting.organization_id == org_id, Posting.first_seen_at >= cutoff)
    ) or 0
    expired = db.scalar(
        select(func.count())
        .select_from(Posting)
        .where(
            Posting.organization_id == org_id,
            Posting.is_active.is_(False),
            Posting.last_seen_at >= cutoff,
        )
    ) or 0

    top_rows = db.execute(
        select(
            Posting.industrial_overlay_code,
            Posting.occupation_code,
            func.count().label("n"),
        )
        .where(Posting.organization_id == org_id, Posting.first_seen_at >= cutoff)
        .group_by(Posting.industrial_overlay_code, Posting.occupation_code)
        .order_by(func.count().desc())
        .limit(10)
    ).all()
    top_occupations = [
        {
            "industrial_overlay_code": r.industrial_overlay_code,
            "occupation_code": r.occupation_code,
            "count": r.n,
        }
        for r in top_rows
    ]

    return OrgHiringActivity(
        organization_id=org_id,
        window_days=window_days,
        active_postings=int(active),
        new_postings=int(new),
        expired_postings=int(expired),
        top_occupations=top_occupations,
    )
