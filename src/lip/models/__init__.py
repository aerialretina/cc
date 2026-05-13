"""SQLAlchemy ORM models for the labor graph.

Entity types follow §0.1 of the build plan:

  Person, Organization, Role, Project, HiringEvent, Posting,
  CompensationRecord, RecruiterInteraction.

Design rule (§0.1): raw scraped data is separated from enriched canonical
records. ``RawPosting`` stores the source-of-truth scrape; ``Posting``
holds the deduplicated, enriched record that downstream queries hit.
"""

from lip.models.base import Base, TimestampMixin
from lip.models.compensation import CompensationRecord
from lip.models.hiring import HiringEvent
from lip.models.lmi import LmiSnapshot
from lip.models.organization import Organization
from lip.models.person import Person
from lip.models.posting import Posting, RawPosting
from lip.models.project import Project
from lip.models.recruiter import RecruiterInteraction
from lip.models.role import Role
from lip.models.skill import Skill

__all__ = [
    "Base",
    "CompensationRecord",
    "HiringEvent",
    "LmiSnapshot",
    "Organization",
    "Person",
    "Posting",
    "Project",
    "RawPosting",
    "RecruiterInteraction",
    "Role",
    "Skill",
    "TimestampMixin",
]
