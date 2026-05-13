"""Three-stage dedup pipeline (§1.3).

  Step 1 — Source-level dedup is enforced by the UNIQUE constraint on
           (source, source_posting_id) in RawPosting.
  Step 2 — Cross-source dedup keys raw postings to a canonical Posting
           via normalized (title, company, location) within a rolling
           60-day window.
  Step 3 — Semantic dedup uses sentence embeddings to merge postings that
           differ in title wording but describe the same role.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from lip.config import get_settings
from lip.enrichment.normalize import (
    normalize_company,
    normalize_location,
    normalize_title,
)
from lip.models import Posting, RawPosting

_settings = get_settings()


@dataclass(slots=True)
class DedupKey:
    title_norm: str
    company_norm: str
    location_norm: str

    def hash(self) -> str:
        joined = f"{self.title_norm}|{self.company_norm}|{self.location_norm}"
        return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:32]


def compute_dedup_key(raw: RawPosting) -> DedupKey:
    return DedupKey(
        title_norm=normalize_title(raw.raw_title),
        company_norm=normalize_company(raw.company_raw),
        location_norm=normalize_location(raw.location_raw),
    )


def find_matching_canonical(
    db: Session,
    key: DedupKey,
    *,
    window_days: int | None = None,
) -> Posting | None:
    """Step 2 — return the canonical Posting matching this normalized key
    within the rolling window, if one exists.
    """
    window_days = window_days or _settings.cross_source_dedup_window_days
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    stmt = (
        select(Posting)
        .where(Posting.dedup_key == key.hash())
        .where(Posting.last_seen_at >= cutoff)
        .order_by(Posting.last_seen_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def find_semantic_match(
    db: Session,
    embedding: list[float],
    organization_id: UUID | None,
    *,
    threshold: float | None = None,
    window_days: int | None = None,
) -> Posting | None:
    """Step 3 — find a Posting in the same org window with embedding
    cosine similarity above the configured threshold.

    Uses the pgvector ``<=>`` cosine-distance operator. Returns None if
    no embedding-equipped match exists.
    """
    threshold = threshold or _settings.semantic_dedup_threshold
    window_days = window_days or _settings.cross_source_dedup_window_days
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    distance_cutoff = 1.0 - threshold

    # Use raw SQL for the vector op to keep the dependency surface small;
    # SQLAlchemy 2.0 + pgvector also offers a typed expression, which we
    # adopt once pgvector dialect bindings are added.
    from sqlalchemy import text

    sql = text(
        """
        SELECT id
        FROM posting
        WHERE last_seen_at >= :cutoff
          AND description_embedding IS NOT NULL
          AND (:org_id IS NULL OR organization_id = :org_id)
          AND (description_embedding <=> CAST(:emb AS vector)) < :distance_cutoff
        ORDER BY description_embedding <=> CAST(:emb AS vector)
        LIMIT 1
        """
    )
    row = db.execute(
        sql,
        {
            "cutoff": cutoff,
            "org_id": organization_id,
            "emb": _vector_literal(embedding),
            "distance_cutoff": distance_cutoff,
        },
    ).first()
    if row is None:
        return None
    return db.get(Posting, row.id)


def _vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(f"{v:.6f}" for v in embedding) + "]"
