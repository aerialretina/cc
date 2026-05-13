"""Skill entity — proprietary industrial skills taxonomy (§2.2)."""

from __future__ import annotations

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from lip.models.base import Base, TimestampMixin, UUIDPKMixin

SKILL_CATEGORIES = (
    "technical",
    "software",
    "certification",
    "equipment",
    "methodology",
    "safety",
)


class Skill(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "skill"

    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(
        SAEnum(*SKILL_CATEGORIES, name="skill_category"),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    __table_args__ = (
        Index("ix_skill_category", "category"),
    )
