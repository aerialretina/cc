"""Person entity — canonical identity, not a profile dump."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lip.models.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from lip.models.recruiter import RecruiterInteraction
    from lip.models.role import Role


class Person(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "person"

    # Identity attributes — kept minimal. Profile data lives in roles & events.
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    primary_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    primary_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Consent flag for storage of PII beyond aggregate analytics (§6.2).
    consent_for_storage: Mapped[bool] = mapped_column(nullable=False, default=False)

    roles: Mapped[list[Role]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )
    recruiter_interactions: Mapped[list[RecruiterInteraction]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_person_primary_email",
            "primary_email",
            unique=True,
            postgresql_where="primary_email IS NOT NULL",
        ),
        Index(
            "ix_person_linkedin_url",
            "linkedin_url",
            unique=True,
            postgresql_where="linkedin_url IS NOT NULL",
        ),
    )
