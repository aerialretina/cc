"""Add organization.summary and posting.apply_url.

Revision ID: 20260513_2200
Revises: 20260513_2030
Create Date: 2026-05-13
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260513_2200"
down_revision: str | None = "20260513_2030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organization", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("posting", sa.Column("apply_url", sa.String(1024), nullable=True))


def downgrade() -> None:
    op.drop_column("posting", "apply_url")
    op.drop_column("organization", "summary")
