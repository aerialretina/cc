"""Posting entities — raw scrape and canonical (deduplicated, enriched) record."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lip.models.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from lip.models.organization import Organization


class RawPosting(UUIDPKMixin, TimestampMixin, Base):
    """Immutable raw record of a single scrape event.

    Separation from ``Posting`` enforces the §0.1 design rule that raw
    scraped data and enriched canonical records live in different tables.
    """

    __tablename__ = "raw_posting"

    source: Mapped[str] = mapped_column(String(128), nullable=False)
    source_posting_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)

    raw_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    company_raw: Mapped[str | None] = mapped_column(String(512), nullable=True)
    location_raw: Mapped[str | None] = mapped_column(String(512), nullable=True)
    posted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    salary_raw: Mapped[str | None] = mapped_column(String(512), nullable=True)
    job_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    html_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Free-form bag for source-specific fields without schema migrations.
    extra: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    posting_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("posting.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("source", "source_posting_id", name="uq_raw_posting_source"),
        Index("ix_raw_posting_scraped_at", "scraped_at"),
        Index("ix_raw_posting_html_hash", "html_hash"),
    )


class Posting(UUIDPKMixin, TimestampMixin, Base):
    """Canonical, deduplicated, enriched posting.

    One Posting may aggregate many RawPosting records (cross-source dedup).
    """

    __tablename__ = "posting"

    organization_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    occupation_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    occupation_system: Mapped[str | None] = mapped_column(String(16), nullable=True)
    industrial_overlay_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(32), nullable=True)

    region_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    location_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)

    salary_low: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_high: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    salary_period: Mapped[str | None] = mapped_column(String(16), nullable=True)  # annual/hourly

    skills: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    certifications: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    dedup_key: Mapped[str] = mapped_column(String(128), nullable=False)

    # Confidence on enrichment fields (0..1). See §6.1.
    confidence: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    organization: Mapped[Organization | None] = relationship(back_populates="postings")

    __table_args__ = (
        Index("ix_posting_dedup_key", "dedup_key"),
        Index("ix_posting_active_lastseen", "is_active", "last_seen_at"),
        Index("ix_posting_occupation", "occupation_system", "occupation_code"),
        Index("ix_posting_region", "region_code"),
        Index("ix_posting_skills", "skills", postgresql_using="gin"),
    )
