"""GET /v1/mobility — sector-to-sector transition flows in a region/window."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from lip.api.schemas import MobilityEdge
from lip.db import get_db

router = APIRouter()


@router.get("", response_model=list[MobilityEdge])
def mobility(
    db: Session = Depends(get_db),
    from_sector: str = Query(...),
    to_sector: str = Query(...),
    region: str = Query(...),
    time_window_months: int = Query(default=36, ge=1, le=120),
) -> list[MobilityEdge]:
    """Mobility edges are derived from sequential Role rows on the same Person.

    The graph traversal is implemented once Apache AGE is enabled and the
    Role table contains adequate history.
    """
    _ = db, from_sector, to_sector, region, time_window_months
    return []
