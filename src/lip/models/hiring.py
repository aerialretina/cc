"""HiringEvent — the gold asset: a closed placement / confirmed hire (§0.1, §4.1)."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lip.models.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from lip.models.compensation import CompensationRecord
    from lip.models.organization import Organization
    from lip.models.person import Person
    from lip.models.project import Project
    from lip.models.role import Role


class HiringEvent(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "hiring_event"

    person_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("person.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="RESTRICT"),
        nullable=False,
    )
    role_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("role.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("project.id", ondelete="SET NULL"),
        nullable=True,
    )

    placement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # direct_hire / contract / executive_search

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    early_departure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    source_channel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # how the candidate was sourced (referral / database / outreach / inbound)

    person: Mapped[Person] = relationship()
    organization: Mapped[Organization] = relationship()
    role: Mapped[Role | None] = relationship()
    project: Mapped[Project | None] = relationship()
    compensation: Mapped[list[CompensationRecord]] = relationship(
        back_populates="hiring_event",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_hiring_event_person", "person_id"),
        Index("ix_hiring_event_organization", "organization_id"),
        Index("ix_hiring_event_start_date", "start_date"),
    )
