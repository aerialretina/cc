"""Government data integration (§3).

Connectors fetch on their native schedules and emit time-series into the
data warehouse. Each connector exposes:

  ``fetch(*, since: date | None = None) -> Iterable[dict]``

…so the orchestrator (a Celery beat task) can pull incrementally.
"""
