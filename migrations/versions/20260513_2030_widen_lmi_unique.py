"""Widen lmi_snapshot unique constraint to include industrial_overlay_code.

Two overlays can legitimately share a NOC (e.g. engineering.mechanical
and industrial.reliability-engineer both roll under NOC 21301). The
original constraint locked us to one row per (region, NOC, source,
period), which dropped overlay information. Add overlay to the key so
both rows survive.

Revision ID: 20260513_2030
Revises: 20260513_1900
Create Date: 2026-05-13
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20260513_2030"
down_revision: str | None = "20260513_1900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_lmi_region_occ_src_period", "lmi_snapshot", type_="unique")
    op.create_unique_constraint(
        "uq_lmi_region_occ_overlay_src_period",
        "lmi_snapshot",
        [
            "region_code",
            "occupation_code",
            "industrial_overlay_code",
            "source",
            "observed_period",
        ],
    )


def downgrade() -> None:
    op.drop_constraint("uq_lmi_region_occ_overlay_src_period", "lmi_snapshot", type_="unique")
    op.create_unique_constraint(
        "uq_lmi_region_occ_src_period",
        "lmi_snapshot",
        ["region_code", "occupation_code", "source", "observed_period"],
    )
