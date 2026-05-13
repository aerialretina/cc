"""Project entity — infrastructure / construction project (§4.3)."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lip.models.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from lip.models.organization import Organization
    from lip.models.role import Role


class Project(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "project"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # e.g. "lng", "pipeline", "data-center", "transit", "hospital", "mine".

    owner_org_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="SET NULL"),
        nullable=True,
    )
    epc_contractor_org_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="SET NULL"),
        nullable=True,
    )

    region_code: Mapped[str | None] = mapped_column(String(8), nullable=True)  # ISO-3166-2
    location_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)

    capex_usd: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    estimated_peak_headcount: Mapped[int | None] = mapped_column(Integer, nullable=True)

    announced_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    construction_start_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_completion_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    owner: Mapped[Organization | None] = relationship(foreign_keys=[owner_org_id])
    epc_contractor: Mapped[Organization | None] = relationship(foreign_keys=[epc_contractor_org_id])
    roles: Mapped[list[Role]] = relationship(back_populates="project")

    __table_args__ = (
        Index("ix_project_region", "region_code"),
        Index("ix_project_type", "project_type"),
    )
