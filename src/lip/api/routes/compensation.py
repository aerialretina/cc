"""GET /v1/compensation — placement-verified + posted + modeled comp benchmarks.

Source-reliability weighting (§6.1):
  placement_verified > posted > modeled
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lip.api.schemas import CompensationStats
from lip.db import get_db
from lip.models import CompensationRecord

router = APIRouter()


def _percentile(sorted_values: list[float], p: int) -> float:
    """Linear-interpolated percentile of a sorted list (R-7 / numpy default)."""
    if not sorted_values:
        raise ValueError("empty list")
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


@router.get("", response_model=CompensationStats)
def get_compensation(
    db: Session = Depends(get_db),
    occupation: str = Query(..., description="industrial_overlay_code or occupation_code"),
    occupation_system: str | None = Query(default=None),
    region_code: str | None = Query(default=None),
    seniority: str | None = Query(default=None),
    percentile: str = Query(default="25,50,75,90"),
    currency: str = Query(default="USD"),
    period: str = Query(default="annual"),
) -> CompensationStats:
    try:
        percentiles = [int(p.strip()) for p in percentile.split(",")]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid percentile list") from exc
    if any(p < 1 or p > 99 for p in percentiles):
        raise HTTPException(status_code=400, detail="percentiles must be 1..99")

    stmt = select(CompensationRecord.amount_mid, CompensationRecord.source_type).where(
        CompensationRecord.currency == currency,
        CompensationRecord.period == period,
    )

    occ_match = (
        (CompensationRecord.industrial_overlay_code == occupation)
        | (CompensationRecord.occupation_code == occupation)
    )
    stmt = stmt.where(occ_match)

    if occupation_system:
        stmt = stmt.where(CompensationRecord.occupation_system == occupation_system)
    if region_code:
        stmt = stmt.where(CompensationRecord.region_code == region_code)
    if seniority:
        stmt = stmt.where(CompensationRecord.seniority == seniority)

    rows = db.execute(stmt).all()
    if not rows:
        raise HTTPException(status_code=404, detail="no compensation records match")

    amounts = sorted(float(r.amount_mid) for r in rows)
    percentile_values = {f"p{p}": _percentile(amounts, p) for p in percentiles}

    source_mix: dict[str, int] = {}
    for r in rows:
        source_mix[r.source_type] = source_mix.get(r.source_type, 0) + 1

    return CompensationStats(
        occupation=occupation,
        region=region_code,
        n_observations=len(rows),
        percentiles=percentile_values,
        currency=currency,
        period=period,
        source_mix=source_mix,
    )
