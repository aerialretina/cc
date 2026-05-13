"""RecruiterInteraction — event log capturing CRM activity (§4.1).

Every recruiter action is a data event. The CRM is structured as an event
log, not just a contact database — each event enriches the labor graph.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lip.models.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from lip.models.organization import Organization
    from lip.models.person import Person

EVENT_TYPES = (
    "candidate_introduced",
    "client_interview_scheduled",
    "offer_extended",
    "placement_confirmed",
    "candidate_declined",
    "early_departure",
    "client_engaged",
    "candidate_outreach",
    "candidate_response",
)


class RecruiterInteraction(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "recruiter_interaction"

    event_type: Mapped[str] = mapped_column(
        SAEnum(*EVENT_TYPES, name="recruiter_event_type"),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    person_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("person.id", ondelete="CASCADE"),
        nullable=True,
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="SET NULL"),
        nullable=True,
    )

    recruiter: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # Event-specific payload — kept flexible to avoid migrations for every new
    # event variant. Schemas are validated in the application layer.
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    person: Mapped[Person | None] = relationship(back_populates="recruiter_interactions")
    organization: Mapped[Organization | None] = relationship()

    __table_args__ = (
        Index("ix_recruiter_event_type", "event_type"),
        Index("ix_recruiter_occurred_at", "occurred_at"),
        Index("ix_recruiter_person", "person_id"),
        Index("ix_recruiter_organization", "organization_id"),
    )
