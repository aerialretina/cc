"""Raw archive (S3 / MinIO) + RawPosting upsert."""

from __future__ import annotations

import json
from datetime import datetime

import boto3
from botocore.config import Config as BotoConfig
from sqlalchemy.dialects.postgresql import insert as pg_insert

from lip.config import get_settings
from lip.db import session_scope
from lip.logging import get_logger
from lip.models import RawPosting
from lip.scraping.base import ScrapedPosting

logger = get_logger(__name__)


def _s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=BotoConfig(signature_version="s3v4"),
    )


def _s3_key(source: str, source_posting_id: str, scraped_at: datetime) -> str:
    yyyy_mm_dd = scraped_at.strftime("%Y/%m/%d")
    safe_id = source_posting_id.replace("/", "_")
    return f"raw/{source}/{yyyy_mm_dd}/{safe_id}.json"


def archive_to_s3(posting: ScrapedPosting) -> str:
    """Write raw payload + metadata to object storage, return the key."""
    settings = get_settings()
    key = _s3_key(posting.source, posting.source_posting_id, posting.scraped_at)
    body = json.dumps(
        {
            "source": posting.source,
            "source_posting_id": posting.source_posting_id,
            "source_url": posting.source_url,
            "scraped_at": posting.scraped_at.isoformat(),
            "raw_payload": posting.raw_payload,
            "extra": posting.extra,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    _s3_client().put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
    )
    return key


def upsert_raw_posting(posting: ScrapedPosting, s3_key: str | None = None) -> None:
    """Insert (or no-op update) the RawPosting row.

    Implements §1.3 Step 1 — source-level dedup keyed on
    ``(source, source_posting_id)``.
    """
    stmt = pg_insert(RawPosting).values(
        source=posting.source,
        source_posting_id=posting.source_posting_id,
        source_url=posting.source_url,
        raw_title=posting.raw_title,
        company_raw=posting.company_raw,
        location_raw=posting.location_raw,
        posted_date=posting.posted_date,
        salary_raw=posting.salary_raw,
        job_type=posting.job_type,
        description_text=posting.description_text,
        html_hash=posting.html_hash,
        s3_key=s3_key,
        extra=posting.extra,
        scraped_at=posting.scraped_at,
    )
    # On conflict: refresh scraped_at and last-seen fields, keep original id.
    stmt = stmt.on_conflict_do_update(
        index_elements=["source", "source_posting_id"],
        set_={
            "scraped_at": stmt.excluded.scraped_at,
            "html_hash": stmt.excluded.html_hash,
            "raw_title": stmt.excluded.raw_title,
            "company_raw": stmt.excluded.company_raw,
            "location_raw": stmt.excluded.location_raw,
            "salary_raw": stmt.excluded.salary_raw,
            "description_text": stmt.excluded.description_text,
            "s3_key": stmt.excluded.s3_key,
            "extra": stmt.excluded.extra,
        },
    )
    with session_scope() as db:
        db.execute(stmt)
