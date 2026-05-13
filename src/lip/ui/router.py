"""HTML routes for the plaintext front end."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from lip import __version__
from lip.db import get_db
from lip.models import (
    CompensationRecord,
    HiringEvent,
    Organization,
    Posting,
    Project,
    RawPosting,
)
from lip.scraping.registry import list_spiders
from lip.taxonomy.industrial import INDUSTRIAL_OVERLAY
from lip.ui.render import empty_state, kv_block, page, text_table

router = APIRouter(default_response_class=HTMLResponse)


@router.get("/", include_in_schema=False)
def index(db: Session = Depends(get_db)) -> HTMLResponse:
    stats = _safe_counts(db)
    summary = kv_block(
        [
            ("version", __version__),
            ("canonical postings", stats["postings"]),
            ("active postings", stats["postings_active"]),
            ("raw scrape records", stats["raw_postings"]),
            ("organizations", stats["organizations"]),
            ("projects", stats["projects"]),
            ("hiring events (placements)", stats["hiring_events"]),
            ("compensation records", stats["compensation"]),
            ("registered spiders", list_spiders()),
            ("industrial overlay codes", len(INDUSTRIAL_OVERLAY)),
        ]
    )
    return HTMLResponse(page("Labor Intelligence Platform", summary))


@router.get("/ui/postings", include_in_schema=False)
def postings_view(db: Session = Depends(get_db), limit: int = 50) -> HTMLResponse:
    rows = db.scalars(
        select(Posting).order_by(Posting.last_seen_at.desc()).limit(limit)
    ).all()
    if not rows:
        body = empty_state(
            "canonical postings",
            "Run a spider (`celery -A lip.worker.app worker`) or trigger "
            "`lip.scraping.tasks.run_spider('job_bank_canada')` to ingest postings.",
        )
    else:
        org_names = _org_name_map(db, [p.organization_id for p in rows if p.organization_id])
        body = text_table(
            ["last seen", "title", "org", "region", "overlay", "salary"],
            [
                [
                    p.last_seen_at,
                    _truncate(p.title, 50),
                    _truncate(org_names.get(p.organization_id, ""), 28),
                    p.region_code,
                    p.industrial_overlay_code,
                    _salary_range(p),
                ]
                for p in rows
            ],
        )
    return HTMLResponse(page("Postings — most recent", body))


@router.get("/ui/organizations", include_in_schema=False)
def organizations_view(db: Session = Depends(get_db), limit: int = 50) -> HTMLResponse:
    counts_subq = (
        select(Posting.organization_id, func.count().label("n"))
        .where(Posting.organization_id.is_not(None))
        .group_by(Posting.organization_id)
        .subquery()
    )
    rows = db.execute(
        select(Organization, counts_subq.c.n)
        .join(counts_subq, Organization.id == counts_subq.c.organization_id, isouter=True)
        .order_by(func.coalesce(counts_subq.c.n, 0).desc(), Organization.canonical_name.asc())
        .limit(limit)
    ).all()
    if not rows:
        body = empty_state(
            "organizations",
            "Organizations are created during enrichment when posting "
            "employer names are resolved.",
        )
    else:
        body = text_table(
            ["organization", "sectors", "regions", "postings", "client"],
            [
                [
                    _truncate(org.canonical_name, 40),
                    org.sector_tags,
                    org.operating_regions,
                    int(n or 0),
                    org.is_recruiter_client,
                ]
                for org, n in rows
            ],
        )
    return HTMLResponse(page("Organizations", body))


@router.get("/ui/compensation", include_in_schema=False)
def compensation_view(db: Session = Depends(get_db), limit: int = 50) -> HTMLResponse:
    rows = db.scalars(
        select(CompensationRecord)
        .order_by(CompensationRecord.observed_on.desc())
        .limit(limit)
    ).all()
    if not rows:
        body = empty_state(
            "compensation records",
            "These accrue from `crm.log_placement_confirmed(...)` "
            "(placement_verified) and from posted-salary extraction.",
        )
    else:
        body = text_table(
            ["observed", "overlay", "seniority", "region", "amount mid", "ccy", "source"],
            [
                [
                    r.observed_on,
                    r.industrial_overlay_code,
                    r.seniority,
                    r.region_code,
                    r.amount_mid,
                    r.currency,
                    r.source_type,
                ]
                for r in rows
            ],
        )
    return HTMLResponse(page("Compensation — recent observations", body))


@router.get("/ui/projects", include_in_schema=False)
def projects_view(db: Session = Depends(get_db), limit: int = 50) -> HTMLResponse:
    rows = db.scalars(
        select(Project)
        .order_by(
            Project.construction_start_on.desc().nullslast(),
            Project.announced_on.desc().nullslast(),
        )
        .limit(limit)
    ).all()
    if not rows:
        body = empty_state(
            "projects",
            "Project intelligence (Phase 6) ingests from Dodge, ENR Top 400, "
            "SAM.gov, MERX, and named-project news scraping.",
        )
    else:
        body = text_table(
            ["name", "type", "region", "capex (USD)", "peak headcount", "start"],
            [
                [
                    _truncate(p.name, 40),
                    p.project_type,
                    p.region_code,
                    p.capex_usd,
                    p.estimated_peak_headcount,
                    p.construction_start_on,
                ]
                for p in rows
            ],
        )
    return HTMLResponse(page("Projects", body))


def _safe_counts(db: Session) -> dict[str, int]:
    """Return zero counts if the schema hasn't been migrated yet."""
    out = {
        "postings": 0,
        "postings_active": 0,
        "raw_postings": 0,
        "organizations": 0,
        "projects": 0,
        "hiring_events": 0,
        "compensation": 0,
    }
    pairs = [
        ("postings", select(func.count()).select_from(Posting)),
        (
            "postings_active",
            select(func.count()).select_from(Posting).where(Posting.is_active.is_(True)),
        ),
        ("raw_postings", select(func.count()).select_from(RawPosting)),
        ("organizations", select(func.count()).select_from(Organization)),
        ("projects", select(func.count()).select_from(Project)),
        ("hiring_events", select(func.count()).select_from(HiringEvent)),
        ("compensation", select(func.count()).select_from(CompensationRecord)),
    ]
    for key, stmt in pairs:
        try:
            out[key] = int(db.scalar(stmt) or 0)
        except SQLAlchemyError:
            db.rollback()
    return out


def _org_name_map(db: Session, ids: list) -> dict:
    ids = [i for i in ids if i is not None]
    if not ids:
        return {}
    rows = db.execute(
        select(Organization.id, Organization.canonical_name).where(Organization.id.in_(ids))
    ).all()
    return {r.id: r.canonical_name for r in rows}


def _truncate(text: str | None, n: int) -> str:
    if not text:
        return ""
    return text if len(text) <= n else text[: n - 1] + "…"


def _salary_range(p: Posting) -> str:
    if p.salary_low is None and p.salary_high is None:
        return ""
    low = f"{p.salary_low:,.0f}" if p.salary_low is not None else "?"
    high = f"{p.salary_high:,.0f}" if p.salary_high is not None else "?"
    ccy = p.salary_currency or ""
    period = p.salary_period or ""
    return f"{low}-{high} {ccy} {period}".strip()


__all__ = ["router"]
