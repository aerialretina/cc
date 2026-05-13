"""Celery tasks driving the enrichment pipeline."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from lip.db import session_scope
from lip.enrichment.pipeline import enrich
from lip.logging import get_logger
from lip.models import Posting
from lip.worker import app

logger = get_logger(__name__)


@app.task(name="lip.enrichment.tasks.enrich_raw_posting", bind=True, max_retries=3)
def enrich_raw_posting(self, source: str, source_posting_id: str) -> str | None:
    posting = enrich(source, source_posting_id)
    if posting is None:
        return None
    logger.debug("enriched", source=source, sid=source_posting_id, posting_id=str(posting.id))
    return str(posting.id)


@app.task(name="lip.enrichment.tasks.run_dedup_sweep")
def run_dedup_sweep(stale_after_days: int = 14) -> int:
    """Expire canonical postings that haven't been re-observed in N days.

    Lightcast uses a 60-day rolling dedup window; "active" tightens that
    to a stricter staleness check to reflect that postings drop off
    aggregator sites within 2-3 weeks.
    """
    cutoff = datetime.now(UTC) - timedelta(days=stale_after_days)
    with session_scope() as db:
        result = db.execute(
            update(Posting)
            .where(Posting.is_active.is_(True), Posting.last_seen_at < cutoff)
            .values(is_active=False)
        )
        expired = result.rowcount or 0
    logger.info("dedup_sweep", expired=expired, cutoff=cutoff.isoformat())
    return expired
