"""Celery tasks that drive scraping runs and ingestion."""

from __future__ import annotations

from lip.enrichment.tasks import enrich_raw_posting
from lip.logging import get_logger
from lip.scraping.registry import get_spider
from lip.scraping.storage import archive_to_s3, upsert_raw_posting
from lip.worker import app

logger = get_logger(__name__)


@app.task(name="lip.scraping.tasks.run_spider", bind=True, max_retries=3)
def run_spider(self, source_name: str) -> dict[str, int]:
    """Run a single named spider end-to-end.

    For each scraped posting:
      1. Archive raw payload to S3 (immutable).
      2. Upsert RawPosting row (source-level dedup via unique constraint).
      3. Enqueue enrichment for the canonical pipeline.
    """
    spider_cls = get_spider(source_name)
    spider = spider_cls()
    seen = 0
    archived = 0
    for posting in spider.crawl():
        seen += 1
        try:
            s3_key = archive_to_s3(posting)
        except Exception:
            logger.exception("s3_archive_failed", source=source_name, sid=posting.source_posting_id)
            s3_key = None
        upsert_raw_posting(posting, s3_key=s3_key)
        if s3_key:
            archived += 1
        enrich_raw_posting.delay(posting.source, posting.source_posting_id)

    logger.info("spider_run_complete", source=source_name, seen=seen, archived=archived)
    return {"seen": seen, "archived": archived}
