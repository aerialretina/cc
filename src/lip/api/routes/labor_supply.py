"""GET /v1/labor-supply — government LMI overlaid with our demand signal."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from lip.api.schemas import LaborSupplyMetric
from lip.db import get_db

router = APIRouter()


@router.get("", response_model=list[LaborSupplyMetric])
def labor_supply(
    db: Session = Depends(get_db),
    occupation: str = Query(..., description="NOC or SOC code"),
    region: str = Query(..., description="ISO-3166-2 or Economic Region code"),
    metric: list[str] = Query(default=["employment", "projected_change", "shortage_indicator"]),
) -> list[LaborSupplyMetric]:
    """Read from the government data warehouse (BLS / StatCan).

    Implementation lands when the Phase 3 ETL has populated the
    ``gov_*`` time-series tables. Returns an empty list until then.
    """
    _ = db, metric  # interface stable; query body lands with Phase 3.
    return []
