"""GET /v1/labor-supply — government LMI overlaid with our demand signal."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from lip.api.schemas import LaborSupplyMetric
from lip.db import get_db
from lip.models import LmiSnapshot

router = APIRouter()


@router.get("", response_model=list[LaborSupplyMetric])
def labor_supply(
    db: Session = Depends(get_db),
    occupation: str = Query(..., description="NOC or SOC code"),
    region: str = Query(..., description="ISO-3166-2 region (e.g. CA-AB, US-TX)"),
    source: str | None = Query(default=None, description="Filter by upstream LMI source"),
) -> list[LaborSupplyMetric]:
    stmt = select(LmiSnapshot).where(
        LmiSnapshot.occupation_code == occupation,
        LmiSnapshot.region_code == region,
    )
    if source:
        stmt = stmt.where(LmiSnapshot.source == source)
    stmt = stmt.order_by(LmiSnapshot.observed_period.desc())

    return [
        LaborSupplyMetric(
            occupation_code=r.occupation_code or occupation,
            region_code=r.region_code,
            employment=r.employment,
            projected_change_pct=float(r.projected_change_pct) if r.projected_change_pct is not None else None,
            shortage_indicator=float(r.shortage_indicator) if r.shortage_indicator is not None else None,
            as_of=r.observed_period,
        )
        for r in db.scalars(stmt).all()
    ]
