"""CompensationRecord — salary/rate with provenance and confidence (§2.3)."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lip.models.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from lip.models.hiring import HiringEvent

COMP_SOURCE_TYPES = (
    "placement_verified",
    "posted",
    "modeled",
    "self_reported",
    "third_party",
)


class CompensationRecord(UUIDPKMixin, TimestampMixin, Base):
    """A compensation observation tagged with its provenance.

    Source type ordering matters for §6.1 source-reliability weighting:
    placement-verified > extracted (posted) > modeled.
    """

    __tablename__ = "compensation_record"

    hiring_event_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("hiring_event.id", ondelete="CASCADE"),
        nullable=True,
    )

    occupation_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    occupation_system: Mapped[str | None] = mapped_column(String(16), nullable=True)
    industrial_overlay_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(32), nullable=True)
    region_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(64), nullable=True)

    amount_low: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    amount_mid: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    amount_high: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    period: Mapped[str] = mapped_column(String(16), nullable=False, default="annual")

    source_type: Mapped[str] = mapped_column(
        SAEnum(*COMP_SOURCE_TYPES, name="comp_source_type"),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=0.5)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)

    hiring_event: Mapped[HiringEvent | None] = relationship(back_populates="compensation")

    __table_args__ = (
        Index("ix_comp_occupation", "occupation_system", "occupation_code"),
        Index("ix_comp_region", "region_code"),
        Index("ix_comp_source_type", "source_type"),
        Index("ix_comp_observed_on", "observed_on"),
    )
