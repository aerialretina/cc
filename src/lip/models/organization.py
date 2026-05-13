"""Organization entity — canonical employer registry (§2.4)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lip.models.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from lip.models.posting import Posting
    from lip.models.role import Role


class Organization(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "organization"

    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    aliases: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )

    # Sector tags (construction, energy, EPC, owner, subcontractor, industrial, ...).
    sector_tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )

    naics_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    headcount_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    union_status: Mapped[str | None] = mapped_column(String(32), nullable=True)  # union/non-union/mixed

    # Geography of operations stored as ISO-3166-2 codes (e.g. CA-AB, US-TX).
    operating_regions: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )

    enr_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_recruiter_client: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    careers_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Short factual paragraph describing the org. Sourced at seed time
    # from public company profiles; refreshed periodically.

    roles: Mapped[list[Role]] = relationship(back_populates="organization")
    postings: Mapped[list[Posting]] = relationship(back_populates="organization")

    __table_args__ = (
        Index("ix_organization_naics_code", "naics_code"),
        Index("ix_organization_sector_tags", "sector_tags", postgresql_using="gin"),
        Index("ix_organization_aliases", "aliases", postgresql_using="gin"),
    )
