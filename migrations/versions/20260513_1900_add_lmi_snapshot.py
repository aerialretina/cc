"""Add lmi_snapshot table for government LMI ingestion (§3).

Revision ID: 20260513_1900
Revises: 20260513_0000
Create Date: 2026-05-13
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260513_1900"
down_revision: str | None = "20260513_0000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lmi_snapshot",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("region_code", sa.String(8), nullable=False),
        sa.Column("occupation_system", sa.String(16), nullable=True),
        sa.Column("occupation_code", sa.String(16), nullable=True),
        sa.Column("industrial_overlay_code", sa.String(64), nullable=True),
        sa.Column("employment", sa.Integer, nullable=True),
        sa.Column("median_wage", sa.Numeric(10, 2), nullable=True),
        sa.Column("wage_currency", sa.String(3), nullable=True),
        sa.Column("shortage_indicator", sa.Numeric(3, 2), nullable=True),
        sa.Column("projected_change_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("observed_period", sa.Date, nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "region_code",
            "occupation_code",
            "source",
            "observed_period",
            name="uq_lmi_region_occ_src_period",
        ),
    )
    op.create_index("ix_lmi_region", "lmi_snapshot", ["region_code"])
    op.create_index("ix_lmi_occupation", "lmi_snapshot", ["occupation_system", "occupation_code"])
    op.create_index("ix_lmi_overlay", "lmi_snapshot", ["industrial_overlay_code"])
    op.create_index("ix_lmi_observed", "lmi_snapshot", ["observed_period"])


def downgrade() -> None:
    op.drop_table("lmi_snapshot")
