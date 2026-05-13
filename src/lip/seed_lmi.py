"""Curated Canadian LMI snapshot.

Mirrors the kind of cuts StatCan LFS + SEPH + BuildForce Canada publish
quarterly, scoped to the industrial occupations we recruit into. This
is the seed; the real ETL connectors land with the StatCan WDS work.

Each row: (province x industrial occupation x snapshot quarter) with
employment, median wage, projected change, and a shortage indicator
derived from the LFS unemployment / vacancy ratio.

Idempotent: upserts on (region, occupation_code, source, observed_period).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from lip.models import LmiSnapshot

PERIOD = date(2026, 3, 31)  # Q1 2026 snapshot

# (region, NOC, overlay, employment, median wage CAD, shortage 0..1, proj % 36m, source)
ROWS: list[tuple] = [
    # ---- Construction Project Managers (NOC 70010) — high-shortage roles ----
    ("CA-AB", "70010", "construction.project-manager", 8400, 132000, 0.82, 11.5, "statcan_lfs"),
    ("CA-BC", "70010", "construction.project-manager", 7100, 128000, 0.78, 9.8, "statcan_lfs"),
    ("CA-ON", "70010", "construction.project-manager", 14200, 135000, 0.74, 7.6, "statcan_lfs"),
    ("CA-QC", "70010", "construction.project-manager", 8900, 122000, 0.65, 5.2, "statcan_lfs"),
    ("CA-SK", "70010", "construction.project-manager", 1800, 118000, 0.71, 6.0, "statcan_lfs"),
    ("CA-MB", "70010", "construction.project-manager", 2100, 115000, 0.66, 4.4, "statcan_lfs"),
    ("CA-NL", "70010", "construction.project-manager", 900, 122000, 0.84, 14.0, "statcan_lfs"),

    # ---- Construction Managers (NOC 70010) - BuildForce overlay ----
    ("CA-AB", "70010", "construction.construction-manager", 5200, 145000, 0.85, 13.0, "buildforce"),
    ("CA-BC", "70010", "construction.construction-manager", 4700, 141000, 0.80, 11.4, "buildforce"),
    ("CA-ON", "70010", "construction.construction-manager", 9100, 148000, 0.79, 10.2, "buildforce"),

    # ---- Construction Superintendents (NOC 72014) ----
    ("CA-AB", "72014", "construction.superintendent", 6800, 118000, 0.79, 9.6, "statcan_lfs"),
    ("CA-BC", "72014", "construction.superintendent", 5200, 116000, 0.75, 7.8, "statcan_lfs"),
    ("CA-ON", "72014", "construction.superintendent", 11400, 121000, 0.71, 6.0, "statcan_lfs"),
    ("CA-QC", "72014", "construction.superintendent", 6800, 109000, 0.62, 4.3, "statcan_lfs"),
    ("CA-SK", "72014", "construction.superintendent", 1500, 112000, 0.69, 5.1, "statcan_lfs"),

    # ---- Estimators (NOC 22303) ----
    ("CA-AB", "22303", "construction.estimator", 3600, 99000, 0.62, 5.4, "statcan_lfs"),
    ("CA-BC", "22303", "construction.estimator", 3200, 102000, 0.58, 4.8, "statcan_lfs"),
    ("CA-ON", "22303", "construction.estimator", 6800, 104000, 0.55, 3.9, "statcan_lfs"),
    ("CA-QC", "22303", "construction.estimator", 3900, 95000, 0.49, 2.7, "statcan_lfs"),

    # ---- Civil / Structural Engineers (NOC 21300) ----
    ("CA-AB", "21300", "engineering.civil", 5400, 112000, 0.66, 7.1, "statcan_lfs"),
    ("CA-BC", "21300", "engineering.civil", 5800, 115000, 0.62, 6.4, "statcan_lfs"),
    ("CA-ON", "21300", "engineering.civil", 14600, 118000, 0.58, 5.2, "statcan_lfs"),
    ("CA-QC", "21300", "engineering.civil", 8700, 109000, 0.51, 3.6, "statcan_lfs"),

    # ---- Mechanical Engineers (NOC 21301) ----
    ("CA-AB", "21301", "engineering.mechanical", 6200, 118000, 0.68, 6.8, "statcan_lfs"),
    ("CA-BC", "21301", "engineering.mechanical", 4100, 116000, 0.59, 5.5, "statcan_lfs"),
    ("CA-ON", "21301", "engineering.mechanical", 13200, 121000, 0.61, 5.9, "statcan_lfs"),
    ("CA-QC", "21301", "engineering.mechanical", 7900, 112000, 0.49, 3.2, "statcan_lfs"),

    # ---- Electrical / Electronics Engineers (NOC 21310) ----
    ("CA-AB", "21310", "engineering.electrical", 3200, 119000, 0.71, 7.4, "statcan_lfs"),
    ("CA-ON", "21310", "engineering.electrical", 11800, 124000, 0.69, 6.8, "statcan_lfs"),
    ("CA-QC", "21310", "engineering.electrical", 7600, 116000, 0.58, 4.9, "statcan_lfs"),

    # ---- Petroleum / Reservoir Engineers (NOC 21331) ----
    ("CA-AB", "21331", "energy.reservoir-engineer", 4100, 152000, 0.46, -2.4, "statcan_lfs"),
    ("CA-BC", "21331", "energy.reservoir-engineer", 700, 148000, 0.54, 1.2, "statcan_lfs"),
    ("CA-NL", "21331", "energy.reservoir-engineer", 600, 156000, 0.62, 3.6, "statcan_lfs"),

    # ---- Mining Engineers (NOC 21330) ----
    ("CA-BC", "21330", "mining.mine-engineer", 1100, 124000, 0.65, 5.1, "statcan_lfs"),
    ("CA-ON", "21330", "mining.mine-engineer", 1800, 128000, 0.59, 4.4, "statcan_lfs"),
    ("CA-SK", "21330", "mining.mine-engineer", 900, 132000, 0.72, 7.8, "statcan_lfs"),

    # ---- Pipefitters (NOC 72301) - Red Seal ----
    ("CA-AB", "72301", "trades.pipefitter", 9600, 96000, 0.81, 8.4, "statcan_lfs"),
    ("CA-BC", "72301", "trades.pipefitter", 7100, 92000, 0.74, 6.2, "statcan_lfs"),
    ("CA-ON", "72301", "trades.pipefitter", 10800, 94000, 0.72, 5.4, "statcan_lfs"),
    ("CA-SK", "72301", "trades.pipefitter", 1900, 98000, 0.85, 9.6, "statcan_lfs"),

    # ---- Welders (NOC 72106) ----
    ("CA-AB", "72106", "trades.welder", 13400, 76000, 0.69, 4.8, "statcan_lfs"),
    ("CA-ON", "72106", "trades.welder", 18200, 74000, 0.64, 3.9, "statcan_lfs"),
    ("CA-QC", "72106", "trades.welder", 14800, 71000, 0.58, 2.8, "statcan_lfs"),

    # ---- Powerline Technicians (NOC 72202) ----
    ("CA-ON", "72202", "trades.powerline-technician", 4900, 108000, 0.79, 8.4, "statcan_lfs"),
    ("CA-AB", "72202", "trades.powerline-technician", 2600, 112000, 0.75, 7.2, "statcan_lfs"),
    ("CA-BC", "72202", "trades.powerline-technician", 2100, 110000, 0.71, 6.5, "statcan_lfs"),
    ("CA-MB", "72202", "trades.powerline-technician", 900, 105000, 0.74, 7.0, "statcan_lfs"),

    # ---- Heavy Equipment Operators (NOC 73400) ----
    ("CA-AB", "73400", "trades.heavy-equipment-operator", 18900, 84000, 0.62, 3.4, "statcan_lfs"),
    ("CA-BC", "73400", "trades.heavy-equipment-operator", 14200, 82000, 0.58, 2.8, "statcan_lfs"),
    ("CA-ON", "73400", "trades.heavy-equipment-operator", 21100, 78000, 0.54, 1.9, "statcan_lfs"),

    # ---- Industrial Reliability / Maintenance Engineers (rolled up under NOC 21301) ----
    ("CA-AB", "21301", "industrial.reliability-engineer", 1800, 124000, 0.75, 7.6, "statcan_lfs"),
    ("CA-ON", "21301", "industrial.reliability-engineer", 2400, 119000, 0.68, 5.9, "statcan_lfs"),
]


def apply(db: Session) -> SeedLmiResult:
    added = 0
    refreshed = 0
    for region, noc, overlay, emp, wage, shortage, proj, source in ROWS:
        existing = db.execute(
            select(LmiSnapshot).where(
                LmiSnapshot.region_code == region,
                LmiSnapshot.occupation_code == noc,
                LmiSnapshot.source == source,
                LmiSnapshot.observed_period == PERIOD,
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.industrial_overlay_code = overlay
            existing.employment = emp
            existing.median_wage = Decimal(str(wage))
            existing.shortage_indicator = Decimal(str(shortage))
            existing.projected_change_pct = Decimal(str(proj))
            refreshed += 1
            continue
        db.add(
            LmiSnapshot(
                region_code=region,
                occupation_system="NOC",
                occupation_code=noc,
                industrial_overlay_code=overlay,
                employment=emp,
                median_wage=Decimal(str(wage)),
                wage_currency="CAD",
                shortage_indicator=Decimal(str(shortage)),
                projected_change_pct=Decimal(str(proj)),
                observed_period=PERIOD,
                source=source,
            )
        )
        added += 1
    db.commit()
    return SeedLmiResult(added=added, refreshed=refreshed, total_rows=added + refreshed)


class SeedLmiResult(BaseModel):
    added: int
    refreshed: int
    total_rows: int
