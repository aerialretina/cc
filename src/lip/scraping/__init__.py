"""Scraping layer.

See §1 of the build plan. The architecture is:

    Scheduler (Celery beat)
        → Spider (per-source) emits ScrapedPosting records
        → Raw archive (S3 / MinIO) stores the immutable HTML/JSON
        → ingest() upserts a RawPosting row
        → enrichment pipeline picks it up
"""
