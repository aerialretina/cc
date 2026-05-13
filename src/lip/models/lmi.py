"""Labor Market Information snapshot (§3).

A flat, time-stamped fact table of employment + wage + shortage signals
sourced from government LMI providers (StatCan LFS / SEPH, BuildForce
Canada, BLS QCEW / OEWS). One row per (region x occupation x source x
observed_period).

Modeled as a snapshot rather than an event stream because most
upstream providers publish monthly or quarterly bulletins — we ingest
the latest release as a full replace and keep history for trend lines.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from lip.models.base import Base, TimestampMixin, UUIDPKMixin


class LmiSnapshot(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "lmi_snapshot"

    region_code: Mapped[str] = mapped_column(String(8), nullable=False)
    occupation_system: Mapped[str | None] = mapped_column(String(16), nullable=True)  # NOC / SOC
    occupation_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    industrial_overlay_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    employment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    median_wage: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    wage_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # 0..1 — higher = tighter labor market.
    shortage_indicator: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)

    # Projected change in employment over the next 36 months (percent).
    projected_change_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    observed_period: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    # e.g. "statcan_lfs", "statcan_seph", "buildforce", "bls_qcew", "bls_oews"

    __table_args__ = (
        UniqueConstraint(
            "region_code",
            "occupation_code",
            "industrial_overlay_code",
            "source",
            "observed_period",
            name="uq_lmi_region_occ_overlay_src_period",
        ),
        Index("ix_lmi_region", "region_code"),
        Index("ix_lmi_occupation", "occupation_system", "occupation_code"),
        Index("ix_lmi_overlay", "industrial_overlay_code"),
        Index("ix_lmi_observed", "observed_period"),
    )
