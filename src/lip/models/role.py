"""Role entity — a specific position held by a person at an org over a time range."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lip.models.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from lip.models.organization import Organization
    from lip.models.person import Person
    from lip.models.project import Project


class Role(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "role"

    person_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("person.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="RESTRICT"),
        nullable=False,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("project.id", ondelete="SET NULL"),
        nullable=True,
    )

    title_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    occupation_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    occupation_system: Mapped[str | None] = mapped_column(String(16), nullable=True)  # NOC / SOC
    industrial_overlay_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Extracted skill list (canonical skill names, not free text).
    skills: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )

    started_on: Mapped[date] = mapped_column(Date, nullable=False)
    ended_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    person: Mapped[Person] = relationship(back_populates="roles")
    organization: Mapped[Organization] = relationship(back_populates="roles")
    project: Mapped[Project | None] = relationship(back_populates="roles")

    __table_args__ = (
        Index("ix_role_person", "person_id"),
        Index("ix_role_organization", "organization_id"),
        Index("ix_role_occupation", "occupation_system", "occupation_code"),
        Index("ix_role_skills", "skills", postgresql_using="gin"),
    )
