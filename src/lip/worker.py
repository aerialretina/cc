"""Celery application — task dispatch for scraping + enrichment pipelines."""

from celery import Celery
from celery.schedules import crontab

from lip.config import get_settings

settings = get_settings()

app = Celery(
    "lip",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "lip.scraping.tasks",
        "lip.enrichment.tasks",
    ],
)

app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_default_queue="lip-default",
    broker_connection_retry_on_startup=True,
    timezone="UTC",
)

app.conf.beat_schedule = {
    # Tier 2 niche board: 12h cadence per §1.2.
    "scrape-job-bank-canada-12h": {
        "task": "lip.scraping.tasks.run_spider",
        "schedule": crontab(minute=0, hour="*/12"),
        "args": ("job_bank_canada",),
    },
    # Cross-source dedup sweep — runs after every scrape cycle.
    "dedup-sweep-hourly": {
        "task": "lip.enrichment.tasks.run_dedup_sweep",
        "schedule": crontab(minute=15),
    },
}
