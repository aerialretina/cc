"""Admin endpoints — operator-only triggers for ingestion.

These bypass Celery and run the work synchronously inside the request
handler so a single-machine Fly deploy (no worker, no Redis) can still
ingest data. Long scrapes should still go through the worker once one
is provisioned.

Auth: ``X-Admin-Token`` header must equal ``LIP_ADMIN_TOKEN``. If the
env var is unset, all admin endpoints return 503 — there is no
implicit-open mode.
"""

from __future__ import annotations

import secrets
import time

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lip.config import get_settings
from lip.db import get_db
from lip.enrichment.pipeline import _enrich_in_session
from lip.logging import get_logger
from lip.models import Posting, RawPosting
from lip.scraping.registry import get_spider, list_spiders
from lip.scraping.storage import archive_to_s3, upsert_raw_posting

logger = get_logger(__name__)
router = APIRouter()


class ScrapeResult(BaseModel):
    spider: str
    seen: int
    ingested_raw: int
    enriched: int
    took_seconds: float
    canonical_postings_total: int
    raw_postings_total: int
    upstream_error: str | None = None


class SeedDemoResult(BaseModel):
    organizations_added: int
    postings_added: int
    compensation_added: int
    projects_added: int
    canonical_postings_total: int
    raw_postings_total: int


def _require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    expected = get_settings().admin_token
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="LIP_ADMIN_TOKEN is not set on the server",
        )
    if x_admin_token is None or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=401, detail="invalid admin token")


@router.get("/spiders", dependencies=[Depends(_require_admin)])
def spiders() -> dict[str, list[str]]:
    return {"spiders": list_spiders()}


@router.post("/scrape/{name}", response_model=ScrapeResult, dependencies=[Depends(_require_admin)])
def scrape(
    name: str,
    db: Session = Depends(get_db),
    max_postings: int = 200,
) -> ScrapeResult:
    """Run a registered spider end-to-end, synchronously.

    Pipeline per posting:
      1. ``upsert_raw_posting`` (source-level dedup, §1.3 Step 1).
      2. ``_enrich_in_session`` (cross-source dedup + enrichment).
      3. ``archive_to_s3`` if configured (no-op on Fly without S3).

    ``max_postings`` caps the run so we fit comfortably inside Fly's
    HTTP timeout; raise it once a worker process is provisioned.
    """
    try:
        spider_cls = get_spider(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    spider = spider_cls()
    started = time.monotonic()
    seen = 0
    ingested = 0
    enriched = 0
    upstream_error: str | None = None

    # Spider iteration is wrapped so a flaky source (or an exhausted retry
    # chain) returns a partial-success summary instead of a 500.
    try:
        for scraped in spider.crawl():
            seen += 1
            try:
                s3_key = archive_to_s3(scraped)
            except Exception:
                logger.exception("s3_archive_failed", source=name, sid=scraped.source_posting_id)
                s3_key = None
            upsert_raw_posting(scraped, s3_key=s3_key)
            ingested += 1

            raw = db.execute(
                select(RawPosting).where(
                    RawPosting.source == scraped.source,
                    RawPosting.source_posting_id == scraped.source_posting_id,
                )
            ).scalar_one_or_none()
            if raw is not None:
                try:
                    _enrich_in_session(db, raw)
                    db.commit()
                    enriched += 1
                except Exception:
                    db.rollback()
                    logger.exception("enrich_failed", source=name, sid=scraped.source_posting_id)

            if seen >= max_postings:
                break
    except Exception as e:
        logger.exception("spider_crawl_failed", source=name)
        upstream_error = f"{type(e).__name__}: {e}"

    canonical_total = int(db.scalar(select(func.count()).select_from(Posting)) or 0)
    raw_total = int(db.scalar(select(func.count()).select_from(RawPosting)) or 0)

    return ScrapeResult(
        spider=name,
        seen=seen,
        ingested_raw=ingested,
        enriched=enriched,
        took_seconds=round(time.monotonic() - started, 2),
        canonical_postings_total=canonical_total,
        raw_postings_total=raw_total,
        upstream_error=upstream_error,
    )


@router.post(
    "/seed-demo",
    response_model=SeedDemoResult,
    dependencies=[Depends(_require_admin)],
)
def seed_demo(db: Session = Depends(get_db)) -> SeedDemoResult:
    """Insert a small set of realistic industrial postings + orgs.

    Used to populate the UI when the live spider is temporarily blocked
    (upstream 5xx, geo-blocked egress, etc.). Idempotent — re-running
    refreshes ``last_seen_at`` on existing rows rather than duplicating.
    """
    from lip.seed_demo import apply

    return apply(db)
