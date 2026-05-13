"""HTML routes for the front end."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import desc, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from lip.db import get_db
from lip.government.registry import all_connector_classes
from lip.models import (
    CompensationRecord,
    HiringEvent,
    LmiSnapshot,
    Organization,
    Posting,
    Project,
    RawPosting,
)
from lip.scraping.registry import all_spider_classes
from lip.ui.render import (
    LinkedRow,
    Raw,
    card,
    card_grid,
    empty_state,
    fmt_money,
    fmt_salary,
    kv,
    kv_grid,
    page,
    pill,
    pills,
    shortage_pill,
    stat,
    stat_grid,
    table,
)

router = APIRouter(default_response_class=HTMLResponse)


# ============================================================
# Home — dashboard
# ============================================================

@router.get("/", include_in_schema=False)
def index(db: Session = Depends(get_db)) -> HTMLResponse:
    counts = _safe_counts(db)

    # ---- top hiring organizations (by active posting count) --------------
    try:
        top_orgs = db.execute(
            select(Organization, func.count(Posting.id).label("n"))
            .join(Posting, Posting.organization_id == Organization.id)
            .where(Posting.is_active.is_(True))
            .group_by(Organization.id)
            .order_by(func.count(Posting.id).desc())
            .limit(8)
        ).all()
    except SQLAlchemyError:
        db.rollback()
        top_orgs = []

    # ---- top regions by active postings ----------------------------------
    try:
        top_regions = db.execute(
            select(Posting.region_code, func.count().label("n"))
            .where(Posting.is_active.is_(True), Posting.region_code.is_not(None))
            .group_by(Posting.region_code)
            .order_by(func.count().desc())
            .limit(8)
        ).all()
    except SQLAlchemyError:
        db.rollback()
        top_regions = []

    # ---- tightest labor markets ------------------------------------------
    try:
        top_shortage = db.scalars(
            select(LmiSnapshot)
            .order_by(LmiSnapshot.shortage_indicator.desc().nullslast())
            .limit(6)
        ).all()
    except SQLAlchemyError:
        db.rollback()
        top_shortage = []

    # ---- recent postings -------------------------------------------------
    try:
        recent = db.scalars(
            select(Posting).order_by(Posting.last_seen_at.desc()).limit(8)
        ).all()
        org_lookup = _org_lookup(db, [p.organization_id for p in recent])
    except SQLAlchemyError:
        db.rollback()
        recent = []
        org_lookup = {}

    # ---- upcoming projects (closest to construction start) ---------------
    try:
        upcoming = db.scalars(
            select(Project)
            .order_by(Project.construction_start_on.desc().nullslast())
            .limit(6)
        ).all()
    except SQLAlchemyError:
        db.rollback()
        upcoming = []

    sections: list[str] = []

    sections.append(stat_grid([
        stat("Active postings", counts["postings_active"],
             sub=f"{counts['postings']:,} total"),
        stat("Organizations", counts["organizations"],
             sub=f"{sum(1 for o, _ in top_orgs if (o.is_recruiter_client or False))} client" if top_orgs else None),
        stat("Tracked projects", counts["projects"]),
        stat("LMI snapshot rows", counts["lmi"]),
        stat("Placements", counts["hiring_events"],
             sub=f"{counts['compensation']:,} comp records"),
        stat("Raw scrape records", counts["raw_postings"]),
    ]))

    if top_orgs:
        sections.append('<h2>Top hiring employers</h2>')
        sections.append(table(
            ["Organization", "Sectors", "Regions", "Active postings"],
            [
                [
                    LinkedRow(f"/ui/organizations/{o.id}"),
                    o.canonical_name,
                    Raw(pills(o.sector_tags[:3]) if o.sector_tags else "—"),
                    ", ".join((o.operating_regions or [])[:3]) or "—",
                    int(n),
                ]
                for o, n in top_orgs
            ],
            right_align=(4,),
        ))

    if top_regions:
        sections.append('<h2>Top regions by active demand</h2>')
        sections.append(table(
            ["Region", "Active postings"],
            [[r.region_code, int(r.n)] for r in top_regions],
            right_align=(2,),
        ))

    if top_shortage:
        sections.append('<h2>Tightest labor markets</h2>')
        sections.append(table(
            ["Occupation", "Region", "Shortage", "Employment", "Median wage", "36m projection"],
            [
                [
                    s.industrial_overlay_code or s.occupation_code or "—",
                    s.region_code,
                    Raw(shortage_pill(s.shortage_indicator)),
                    s.employment,
                    Raw(_money(s.median_wage, s.wage_currency)),
                    Raw(_pct(s.projected_change_pct)),
                ]
                for s in top_shortage
            ],
            right_align=(4, 5),
        ))

    if recent:
        sections.append('<h2>Recently observed postings</h2>')
        sections.append(table(
            ["Title", "Organization", "Region", "Seniority", "Salary", "Last seen"],
            [
                [
                    LinkedRow(f"/ui/postings/{p.id}"),
                    p.title,
                    Raw(_org_link(p.organization_id, org_lookup)),
                    p.region_code or "—",
                    Raw(pill(p.seniority) if p.seniority else "—"),
                    Raw(fmt_salary(p.salary_low, p.salary_high, p.salary_currency, p.salary_period)),
                    p.last_seen_at,
                ]
                for p in recent
            ],
        ))

    if upcoming:
        sections.append('<h2>Largest tracked projects</h2>')
        sections.append(table(
            ["Project", "Type", "Region", "Capex (USD)", "Peak headcount", "Construction start"],
            [
                [
                    LinkedRow(f"/ui/projects/{pr.id}"),
                    pr.name,
                    Raw(pill(pr.project_type, variant="accent") if pr.project_type else "—"),
                    pr.region_code or "—",
                    Raw(fmt_money(pr.capex_usd)),
                    pr.estimated_peak_headcount,
                    pr.construction_start_on,
                ]
                for pr in upcoming
            ],
            right_align=(4, 5),
        ))

    return HTMLResponse(page(
        "Labor Intelligence Platform",
        "".join(sections),
        current_path="/",
        subtitle="Construction, energy, industrial, and trades — Canada primary, US rolling.",
    ))


# ============================================================
# Postings — list + detail
# ============================================================

@router.get("/ui/postings", include_in_schema=False)
def postings_view(
    db: Session = Depends(get_db),
    region: str | None = Query(default=None),
    overlay: str | None = Query(default=None),
    seniority: str | None = Query(default=None),
    sort: str = Query(default="recent"),
    limit: int = Query(default=100, le=500),
) -> HTMLResponse:
    stmt = select(Posting).where(Posting.is_active.is_(True))
    if region:
        stmt = stmt.where(Posting.region_code == region)
    if overlay:
        stmt = stmt.where(Posting.industrial_overlay_code == overlay)
    if seniority:
        stmt = stmt.where(Posting.seniority == seniority)
    if sort == "salary":
        stmt = stmt.order_by(desc(Posting.salary_high).nullslast())
    else:
        stmt = stmt.order_by(Posting.last_seen_at.desc())
    stmt = stmt.limit(limit)

    rows = db.scalars(stmt).all()
    org_lookup = _org_lookup(db, [p.organization_id for p in rows])
    regions = _distinct(db, Posting.region_code)
    overlays = _distinct(db, Posting.industrial_overlay_code)
    seniorities = _distinct(db, Posting.seniority)

    toolbar = (
        '<div class="toolbar"><form method="get">'
        + _select("region", region, [""] + regions, "All regions")
        + _select("overlay", overlay, [""] + overlays, "All occupations")
        + _select("seniority", seniority, [""] + seniorities, "All seniority")
        + _select("sort", sort, ["recent", "salary"], "Sort", {"recent": "Most recent", "salary": "Highest salary"})
        + '<button type="submit">Apply</button></form></div>'
    )

    if not rows:
        body = toolbar + empty_state(
            "matching postings",
            "Try clearing a filter, or click Run workflow on seed-demo to load the Canadian seed dataset.",
        )
    else:
        body = toolbar + table(
            ["Title", "Organization", "Region", "Seniority", "Salary", "Last seen"],
            [
                [
                    LinkedRow(f"/ui/postings/{p.id}"),
                    p.title,
                    Raw(_org_link(p.organization_id, org_lookup)),
                    p.region_code or "—",
                    Raw(pill(p.seniority) if p.seniority else "—"),
                    Raw(fmt_salary(p.salary_low, p.salary_high, p.salary_currency, p.salary_period)),
                    p.last_seen_at,
                ]
                for p in rows
            ],
        )
    return HTMLResponse(page(
        "Postings",
        body,
        current_path="/ui/postings",
        subtitle=f"{len(rows):,} active postings",
    ))


@router.get("/ui/postings/{posting_id}", include_in_schema=False)
def posting_detail(posting_id: UUID, db: Session = Depends(get_db)) -> HTMLResponse:
    p = db.get(Posting, posting_id)
    if p is None:
        return HTMLResponse(page("Posting not found", empty_state("posting", f"Unknown id: {posting_id}"),
                                 current_path="/ui/postings"), status_code=404)

    org = db.get(Organization, p.organization_id) if p.organization_id else None
    apply_url = p.apply_url or (org.careers_url if org else None) or (org.website if org else None)

    apply_btn = (
        f'<a class="btn" href="{apply_url}" target="_blank" rel="noopener">Apply / view posting →</a>'
        if apply_url else
        '<span class="muted">No application link recorded.</span>'
    )
    org_link = (
        f'<a href="/ui/organizations/{org.id}">{org.canonical_name}</a>' if org else "—"
    )

    header_pills = pills([
        p.region_code,
        p.seniority,
        f"NOC {p.occupation_code}" if p.occupation_code else None,
        p.industrial_overlay_code,
    ])

    body = [
        '<div class="detail-hero">',
        header_pills,
        f'<div class="detail-meta" style="margin-top:10px">{org_link}'
        + (f' · {p.location_text}' if p.location_text else "") + '</div>',
        f'<div style="margin-top:14px">{apply_btn}</div>',
        '</div>',
        kv_grid([
            kv("Salary", Raw(fmt_salary(p.salary_low, p.salary_high, p.salary_currency, p.salary_period))),
            kv("Region", p.region_code),
            kv("Occupation (NOC/SOC)", p.occupation_code),
            kv("Industrial overlay", p.industrial_overlay_code),
            kv("First seen", p.first_seen_at.date() if p.first_seen_at else None),
            kv("Last seen", p.last_seen_at.date() if p.last_seen_at else None),
            kv("Source observations", p.source_count),
            kv("Status", "Active" if p.is_active else "Expired"),
        ]),
    ]
    if p.skills:
        body.append('<h2>Skills</h2>')
        body.append(pills(p.skills))
    if p.certifications:
        body.append('<h2>Certifications</h2>')
        body.append(pills(p.certifications, variant="accent"))
    if org and org.summary:
        body.append('<h2>About the employer</h2>')
        body.append(f'<div class="detail-summary">{org.summary}</div>')

    return HTMLResponse(page(p.title, "".join(body), current_path="/ui/postings"))


# ============================================================
# Organizations — list + detail
# ============================================================

@router.get("/ui/organizations", include_in_schema=False)
def organizations_view(
    db: Session = Depends(get_db),
    sector: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
) -> HTMLResponse:
    counts_subq = (
        select(Posting.organization_id, func.count().label("n"))
        .where(Posting.organization_id.is_not(None))
        .group_by(Posting.organization_id)
        .subquery()
    )
    stmt = (
        select(Organization, counts_subq.c.n)
        .join(counts_subq, Organization.id == counts_subq.c.organization_id, isouter=True)
        .order_by(func.coalesce(counts_subq.c.n, 0).desc(), Organization.canonical_name.asc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    if sector:
        rows = [r for r in rows if sector in (r[0].sector_tags or [])]

    sector_options = sorted({s for r in rows for s in (r[0].sector_tags or [])})
    toolbar = (
        '<div class="toolbar"><form method="get">'
        + _select("sector", sector, [""] + sector_options, "All sectors")
        + '<button type="submit">Apply</button></form></div>'
    )

    if not rows:
        body = toolbar + empty_state("organizations")
    else:
        cards = [
            card(
                title=org.canonical_name,
                href=f"/ui/organizations/{org.id}",
                meta=Raw(pills(org.sector_tags) if org.sector_tags else "").html,
                body_html=(
                    f'<div class="card-summary">{org.summary[:240]}{"…" if org.summary and len(org.summary) > 240 else ""}</div>'
                    if org.summary else ""
                ),
                footer_left=f'<span class="muted">{", ".join(org.operating_regions[:4]) if org.operating_regions else "—"}</span>',
                footer_right=Raw(
                    f'<span class="num">{int(n or 0)} {"posting" if (n or 0) == 1 else "postings"}</span>'
                ).html + ('  ' + pill("client", variant="accent") if org.is_recruiter_client else ""),
            )
            for org, n in rows
        ]
        body = toolbar + card_grid(cards)

    return HTMLResponse(page(
        "Organizations",
        body,
        current_path="/ui/organizations",
        subtitle=f"{len(rows):,} organizations",
    ))


@router.get("/ui/organizations/{org_id}", include_in_schema=False)
def organization_detail(org_id: UUID, db: Session = Depends(get_db)) -> HTMLResponse:
    org = db.get(Organization, org_id)
    if org is None:
        return HTMLResponse(page("Organization not found",
                                 empty_state("organization", f"Unknown id: {org_id}"),
                                 current_path="/ui/organizations"), status_code=404)

    cutoff = datetime.now(UTC) - timedelta(days=90)
    active = db.scalar(
        select(func.count()).select_from(Posting)
        .where(Posting.organization_id == org_id, Posting.is_active.is_(True))
    ) or 0
    recent_count = db.scalar(
        select(func.count()).select_from(Posting)
        .where(Posting.organization_id == org_id, Posting.first_seen_at >= cutoff)
    ) or 0
    postings = db.scalars(
        select(Posting)
        .where(Posting.organization_id == org_id)
        .order_by(Posting.last_seen_at.desc())
        .limit(50)
    ).all()

    summary_html = org.summary or '<span class="muted">No summary on file.</span>'
    body = [
        '<div class="detail-hero">',
        pills(org.sector_tags or [], variant="accent"),
        f'<div class="detail-summary" style="margin-top:14px">{summary_html}</div>',
        '</div>',
        stat_grid([
            stat("Active postings", int(active)),
            stat("New postings (90d)", int(recent_count)),
            stat("Headcount", org.headcount_estimate or "—"),
            stat("Operating regions", len(org.operating_regions or [])),
        ]),
        kv_grid([
            kv("Aliases", org.aliases or None),
            kv("NAICS", org.naics_code),
            kv("Union status", org.union_status),
            kv("ENR rank", org.enr_rank),
            kv("Regions", org.operating_regions or None),
            kv("Recruiter client", org.is_recruiter_client),
        ]),
    ]
    if org.website:
        body.append(
            f'<p><a class="btn ghost" href="{org.website}" target="_blank" rel="noopener">Company site →</a> '
            + (f'<a class="btn ghost" href="{org.careers_url}" target="_blank" rel="noopener">Careers →</a>'
               if org.careers_url else "")
            + '</p>'
        )
    if postings:
        body.append('<h2>Recent postings</h2>')
        body.append(table(
            ["Title", "Region", "Seniority", "Salary", "Last seen"],
            [
                [
                    LinkedRow(f"/ui/postings/{p.id}"),
                    p.title,
                    p.region_code or "—",
                    Raw(pill(p.seniority) if p.seniority else "—"),
                    Raw(fmt_salary(p.salary_low, p.salary_high, p.salary_currency, p.salary_period)),
                    p.last_seen_at,
                ]
                for p in postings
            ],
        ))

    return HTMLResponse(page(org.canonical_name, "".join(body), current_path="/ui/organizations"))


# ============================================================
# Compensation
# ============================================================

@router.get("/ui/compensation", include_in_schema=False)
def compensation_view(db: Session = Depends(get_db), limit: int = 100) -> HTMLResponse:
    rows = db.scalars(
        select(CompensationRecord)
        .order_by(CompensationRecord.observed_on.desc())
        .limit(limit)
    ).all()
    if not rows:
        body = empty_state("compensation records")
    else:
        body = table(
            ["Observed on", "Occupation overlay", "Seniority", "Region", "Salary range", "Source type"],
            [
                [
                    r.observed_on,
                    r.industrial_overlay_code,
                    Raw(pill(r.seniority) if r.seniority else "—"),
                    r.region_code,
                    Raw(_comp_range(r)),
                    Raw(_source_pill(r.source_type)),
                ]
                for r in rows
            ],
        )
    return HTMLResponse(page("Compensation", body, current_path="/ui/compensation",
                             subtitle="Placement-verified + posted + modeled — sorted by recency."))


# ============================================================
# Projects — list + detail
# ============================================================

@router.get("/ui/projects", include_in_schema=False)
def projects_view(db: Session = Depends(get_db), limit: int = 100) -> HTMLResponse:
    rows = db.scalars(
        select(Project)
        .order_by(Project.construction_start_on.desc().nullslast(),
                  Project.announced_on.desc().nullslast())
        .limit(limit)
    ).all()
    if not rows:
        body = empty_state("projects")
    else:
        cards = [
            card(
                title=p.name,
                href=f"/ui/projects/{p.id}",
                meta=Raw(pills([p.project_type, p.region_code], variant="accent")).html,
                body_html=(
                    f'<div class="card-summary">{p.location_text or ""}</div>'
                    if p.location_text else ""
                ),
                footer_left=f'<span class="muted">{fmt_money(p.capex_usd)}</span>',
                footer_right=(
                    f'<span class="num">{p.estimated_peak_headcount:,} peak</span>'
                    if p.estimated_peak_headcount else ""
                ),
            )
            for p in rows
        ]
        body = card_grid(cards)
    return HTMLResponse(page("Projects", body, current_path="/ui/projects",
                             subtitle=f"{len(rows):,} tracked projects"))


@router.get("/ui/projects/{project_id}", include_in_schema=False)
def project_detail(project_id: UUID, db: Session = Depends(get_db)) -> HTMLResponse:
    proj = db.get(Project, project_id)
    if proj is None:
        return HTMLResponse(page("Project not found",
                                 empty_state("project", f"Unknown id: {project_id}"),
                                 current_path="/ui/projects"), status_code=404)
    body = [
        '<div class="detail-hero">',
        pills([proj.project_type, proj.region_code], variant="accent"),
        f'<div class="detail-meta" style="margin-top:10px">{proj.location_text or ""}</div>',
        '</div>',
        kv_grid([
            kv("Project type", proj.project_type),
            kv("Region", proj.region_code),
            kv("Location", proj.location_text),
            kv("Capex (USD)", Raw(fmt_money(proj.capex_usd))),
            kv("Peak headcount", proj.estimated_peak_headcount),
            kv("Announced", proj.announced_on),
            kv("Construction start", proj.construction_start_on),
            kv("Expected completion", proj.expected_completion_on),
            kv("Source", proj.source),
        ]),
    ]
    if proj.source_url:
        body.append(f'<p><a class="btn ghost" href="{proj.source_url}" target="_blank" rel="noopener">Source →</a></p>')
    return HTMLResponse(page(proj.name, "".join(body), current_path="/ui/projects"))


# ============================================================
# Sources — coverage page
# ============================================================

_TIER_LABEL = {
    1: "Tier 1 · Company careers",
    2: "Tier 2 · Vertical board",
    3: "Tier 3 · General / agency",
    4: "Tier 4 · Association",
}


@router.get("/ui/sources", include_in_schema=False)
def sources_view(db: Session = Depends(get_db)) -> HTMLResponse:
    spiders = sorted(all_spider_classes(), key=lambda s: (s.tier, s.source_name))
    connectors = sorted(all_connector_classes(),
                        key=lambda c: (c.country, c.name))

    try:
        ingested = dict(db.execute(
            select(RawPosting.source, func.count())
            .group_by(RawPosting.source)
        ).all())
    except SQLAlchemyError:
        db.rollback()
        ingested = {}

    summary = stat_grid([
        stat("Registered spiders", len(spiders),
             sub=f"{sum(1 for s in spiders if s.status == 'live'):,} live"),
        stat("Government connectors", len(connectors),
             sub=f"{sum(1 for c in connectors if getattr(c, 'status', 'scaffolded') == 'live'):,} live"),
        stat("Sources with data", sum(1 for v in ingested.values() if v > 0),
             sub="raw postings ingested"),
        stat("Total raw observations", sum(ingested.values())),
    ])

    body = [summary]

    # Group spiders by tier
    body.append('<h2>Job-posting sources</h2>')
    spider_rows = []
    for s in spiders:
        spider_rows.append([
            LinkedRow(s.homepage or "#"),
            s.source_name,
            Raw(pill(_TIER_LABEL.get(s.tier, f"Tier {s.tier}"), variant="accent")),
            Raw(pills(s.countries) if s.countries else "—"),
            s.description or "—",
            Raw(_status_pill(s.status)),
            ingested.get(s.source_name, 0),
        ])
    body.append(table(
        ["Source name", "Tier", "Countries", "Description", "Status", "Raw postings ingested"],
        spider_rows,
        right_align=(6,),
    ))

    body.append('<h2>Government data connectors</h2>')
    gov_rows = []
    for c in connectors:
        gov_rows.append([
            getattr(c, "country", "—"),
            c.name,
            Raw(pill(c.description or "—")),
            getattr(c, "update_frequency", "—"),
            getattr(c, "granularity", "—"),
            Raw(_status_pill(getattr(c, "status", "scaffolded"))),
        ])
    body.append(table(
        ["Country", "Connector name", "Dataset", "Update cadence", "Granularity", "Status"],
        gov_rows,
    ))

    return HTMLResponse(page(
        "Sources",
        "".join(body),
        current_path="/ui/sources",
        subtitle=f"{len(spiders)} spiders · {len(connectors)} government connectors",
    ))


def _status_pill(status: str) -> str:
    if status == "live":
        return pill("live", variant="good")
    if status == "scaffolded":
        return pill("scaffolded", variant="warn")
    return pill(status or "—")


# ============================================================
# LMI
# ============================================================

@router.get("/ui/lmi", include_in_schema=False)
def lmi_view(db: Session = Depends(get_db),
             region: str | None = Query(default=None),
             limit: int = Query(default=200, le=1000)) -> HTMLResponse:
    stmt = select(LmiSnapshot).order_by(
        LmiSnapshot.shortage_indicator.desc().nullslast(),
        LmiSnapshot.region_code.asc(),
    )
    if region:
        stmt = stmt.where(LmiSnapshot.region_code == region)
    rows = db.scalars(stmt.limit(limit)).all()
    regions = _distinct(db, LmiSnapshot.region_code)
    toolbar = (
        '<div class="toolbar"><form method="get">'
        + _select("region", region, [""] + regions, "All regions")
        + '<button type="submit">Apply</button></form></div>'
    )
    if not rows:
        body = toolbar + empty_state(
            "LMI snapshots",
            "Click Run workflow on seed-lmi to load the StatCan / BuildForce snapshot.",
        )
    else:
        body = toolbar + table(
            ["Occupation overlay", "Region", "NOC code", "Shortage", "Employed", "Median wage", "36m projection", "Source dataset"],
            [
                [
                    r.industrial_overlay_code or "—",
                    r.region_code,
                    Raw(pill(r.occupation_code, variant="mono") if r.occupation_code else "—"),
                    Raw(shortage_pill(r.shortage_indicator)),
                    r.employment,
                    Raw(_money(r.median_wage, r.wage_currency)),
                    Raw(_pct(r.projected_change_pct)),
                    Raw(pill(r.source)),
                ]
                for r in rows
            ],
            right_align=(5, 6),
        )
    return HTMLResponse(page(
        "Labor Market",
        body,
        current_path="/ui/lmi",
        subtitle="Government LMI snapshot (StatCan LFS + BuildForce). Sorted by shortage indicator.",
    ))


# ============================================================
# helpers
# ============================================================

def _safe_counts(db: Session) -> dict[str, int]:
    out = {"postings": 0, "postings_active": 0, "raw_postings": 0,
           "organizations": 0, "projects": 0, "hiring_events": 0,
           "compensation": 0, "lmi": 0}
    pairs = [
        ("postings", select(func.count()).select_from(Posting)),
        ("postings_active",
         select(func.count()).select_from(Posting).where(Posting.is_active.is_(True))),
        ("raw_postings", select(func.count()).select_from(RawPosting)),
        ("organizations", select(func.count()).select_from(Organization)),
        ("projects", select(func.count()).select_from(Project)),
        ("hiring_events", select(func.count()).select_from(HiringEvent)),
        ("compensation", select(func.count()).select_from(CompensationRecord)),
        ("lmi", select(func.count()).select_from(LmiSnapshot)),
    ]
    for key, stmt in pairs:
        try:
            out[key] = int(db.scalar(stmt) or 0)
        except SQLAlchemyError:
            db.rollback()
    return out


def _org_lookup(db: Session, ids: list) -> dict:
    ids = [i for i in ids if i is not None]
    if not ids:
        return {}
    rows = db.execute(
        select(Organization.id, Organization.canonical_name).where(Organization.id.in_(ids))
    ).all()
    return {r.id: r.canonical_name for r in rows}


def _org_link(org_id, lookup: dict) -> str:
    if not org_id:
        return "—"
    name = lookup.get(org_id, "")
    if not name:
        return "—"
    import html as _html
    return f'<a href="/ui/organizations/{org_id}">{_html.escape(name)}</a>'


def _distinct(db: Session, col) -> list:
    try:
        rows = db.execute(
            select(col).where(col.is_not(None)).distinct().order_by(col.asc())
        ).all()
    except SQLAlchemyError:
        db.rollback()
        return []
    return [r[0] for r in rows if r[0]]


def _select(name: str, value, options: list, default_label: str, labels: dict | None = None) -> str:
    import html as _html
    parts = [f'<select name="{name}">']
    for opt in options:
        label = (labels or {}).get(opt) if labels else None
        if label is None:
            label = opt or default_label
        sel = " selected" if (value or "") == opt else ""
        parts.append(f'<option value="{_html.escape(str(opt))}"{sel}>{_html.escape(str(label))}</option>')
    parts.append('</select>')
    return "".join(parts)


def _money(value, currency=None) -> str:
    if value is None:
        return "—"
    import html as _html
    s = f"${float(value):,.0f}"
    if currency:
        s += f" {currency}"
    return _html.escape(s)


def _pct(value) -> str:
    if value is None:
        return '<span class="muted">—</span>'
    v = float(value)
    variant = "good" if v >= 5 else ("warn" if v >= 0 else "danger")
    return pill(f"{v:+.1f}%", variant=variant)


def _comp_range(r: CompensationRecord) -> str:
    import html as _html
    if r.amount_low is not None and r.amount_high is not None:
        s = f"${float(r.amount_low) / 1000:.0f}k–${float(r.amount_high) / 1000:.0f}k"
    elif r.amount_mid is not None:
        s = f"${float(r.amount_mid) / 1000:.0f}k"
    else:
        s = "—"
    if r.currency:
        s += f" {r.currency}"
    return _html.escape(s)


def _source_pill(source_type: str) -> str:
    variant = {
        "placement_verified": "good",
        "posted": "accent",
        "modeled": "warn",
        "self_reported": "",
        "third_party": "",
    }.get(source_type or "", "")
    return pill(source_type or "—", variant=variant)


__all__ = ["router"]
