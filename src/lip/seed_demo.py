"""Realistic demo data for the UI.

Inserts a handful of canonical organizations, postings, projects, and
compensation records that mirror the kind of work the recruiting
business actually places. Idempotent — re-running upserts on canonical
name / dedup key so the UI populates without duplicating.

Used by ``POST /admin/seed-demo`` when the live spiders are blocked
upstream and we still need a populated front end.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lip.api.routes.admin import SeedDemoResult
from lip.models import (
    CompensationRecord,
    Organization,
    Posting,
    Project,
    RawPosting,
)

NOW = datetime.now(UTC)
TODAY = date.today()

ORGS: list[dict] = [
    {
        "canonical_name": "PCL Construction Group",
        "aliases": ["PCL Constructors", "PCL"],
        "sector_tags": ["construction", "epc"],
        "naics_code": "236220",
        "headcount_estimate": 5400,
        "operating_regions": ["CA-AB", "CA-BC", "CA-ON", "US-CO", "US-CA"],
        "website": "https://www.pcl.com",
        "careers_url": "https://www.pcl.com/careers",
        "enr_rank": 7,
        "is_recruiter_client": True,
    },
    {
        "canonical_name": "Bechtel Corporation",
        "aliases": ["Bechtel"],
        "sector_tags": ["construction", "epc", "energy"],
        "naics_code": "236210",
        "headcount_estimate": 55000,
        "operating_regions": ["US-TX", "US-LA", "US-VA", "CA-BC"],
        "website": "https://www.bechtel.com",
        "enr_rank": 1,
        "is_recruiter_client": False,
    },
    {
        "canonical_name": "Suncor Energy",
        "aliases": ["Suncor"],
        "sector_tags": ["energy", "owner", "oil-gas"],
        "naics_code": "211110",
        "headcount_estimate": 15000,
        "operating_regions": ["CA-AB", "CA-ON"],
        "website": "https://www.suncor.com",
        "is_recruiter_client": True,
    },
    {
        "canonical_name": "AtkinsRéalis",
        "aliases": ["SNC-Lavalin", "AtkinsRealis"],
        "sector_tags": ["construction", "engineering", "epc"],
        "naics_code": "541330",
        "headcount_estimate": 36000,
        "operating_regions": ["CA-QC", "CA-ON", "CA-AB", "US-NY"],
        "website": "https://www.atkinsrealis.com",
        "is_recruiter_client": True,
    },
    {
        "canonical_name": "Kiewit Corporation",
        "aliases": ["Kiewit"],
        "sector_tags": ["construction", "epc", "infrastructure"],
        "naics_code": "237310",
        "headcount_estimate": 28000,
        "operating_regions": ["US-NE", "US-TX", "CA-AB", "CA-BC"],
        "website": "https://www.kiewit.com",
        "enr_rank": 4,
        "is_recruiter_client": False,
    },
]

POSTINGS: list[dict] = [
    {
        "title": "Senior Project Manager - Infrastructure",
        "org": "PCL Construction Group",
        "region": "CA-AB",
        "location": "Edmonton, AB",
        "overlay": "construction.project-manager",
        "occupation_system": "NOC", "occupation_code": "70010",
        "seniority": "senior",
        "salary_low": 130000, "salary_high": 165000, "currency": "CAD", "period": "annual",
        "skills": ["scheduling", "procurement", "cost control", "stakeholder management"],
        "certifications": ["PMP"],
    },
    {
        "title": "Civil Superintendent",
        "org": "PCL Construction Group",
        "region": "CA-AB",
        "location": "Fort McMurray, AB",
        "overlay": "construction.superintendent",
        "occupation_system": "NOC", "occupation_code": "72014",
        "seniority": "senior",
        "salary_low": 110000, "salary_high": 140000, "currency": "CAD", "period": "annual",
        "skills": ["concrete", "earthworks", "site logistics", "safety leadership"],
    },
    {
        "title": "Estimator - Heavy Civil",
        "org": "PCL Construction Group",
        "region": "CA-ON",
        "location": "Toronto, ON",
        "overlay": "construction.estimator",
        "occupation_system": "NOC", "occupation_code": "22303",
        "seniority": "intermediate",
        "salary_low": 95000, "salary_high": 125000, "currency": "CAD", "period": "annual",
        "skills": ["takeoff", "quantity surveying", "tendering"],
        "certifications": ["CET"],
    },
    {
        "title": "Completions Engineer",
        "org": "Suncor Energy",
        "region": "CA-AB",
        "location": "Fort McMurray, AB",
        "overlay": "energy.completions-engineer",
        "occupation_system": "NOC", "occupation_code": "21331",
        "seniority": "intermediate",
        "salary_low": 130000, "salary_high": 175000, "currency": "CAD", "period": "annual",
        "skills": ["well intervention", "pressure testing", "commissioning"],
        "certifications": ["PEng"],
    },
    {
        "title": "Reservoir Engineer",
        "org": "Suncor Energy",
        "region": "CA-AB",
        "location": "Calgary, AB",
        "overlay": "energy.reservoir-engineer",
        "occupation_system": "NOC", "occupation_code": "21331",
        "seniority": "senior",
        "salary_low": 145000, "salary_high": 185000, "currency": "CAD", "period": "annual",
        "skills": ["reservoir simulation", "decline curve analysis", "Petrel"],
        "certifications": ["PEng"],
    },
    {
        "title": "Maintenance Superintendent",
        "org": "Suncor Energy",
        "region": "CA-AB",
        "location": "Fort McMurray, AB",
        "overlay": "industrial.maintenance-superintendent",
        "occupation_system": "NOC", "occupation_code": "72014",
        "seniority": "senior",
        "salary_low": 120000, "salary_high": 150000, "currency": "CAD", "period": "annual",
        "skills": ["turnaround planning", "reliability", "SAP PM"],
    },
    {
        "title": "Process Engineer",
        "org": "Bechtel Corporation",
        "region": "US-TX",
        "location": "Houston, TX",
        "overlay": "industrial.process-engineer",
        "occupation_system": "SOC", "occupation_code": "17-2041",
        "seniority": "intermediate",
        "salary_low": 110000, "salary_high": 145000, "currency": "USD", "period": "annual",
        "skills": ["HYSYS", "P&IDs", "LNG", "PSM"],
        "certifications": ["PE"],
    },
    {
        "title": "Site Superintendent - LNG",
        "org": "Bechtel Corporation",
        "region": "US-LA",
        "location": "Sabine Pass, LA",
        "overlay": "construction.superintendent",
        "occupation_system": "SOC", "occupation_code": "47-1011",
        "seniority": "senior",
        "salary_low": 125000, "salary_high": 160000, "currency": "USD", "period": "annual",
        "skills": ["LNG", "mechanical", "piping", "subcontractor management"],
        "certifications": ["OSHA 30"],
    },
    {
        "title": "QA/QC Manager",
        "org": "Bechtel Corporation",
        "region": "US-LA",
        "location": "Lake Charles, LA",
        "overlay": "construction.qaqc",
        "occupation_system": "SOC", "occupation_code": "13-1041",
        "seniority": "senior",
        "salary_low": 105000, "salary_high": 135000, "currency": "USD", "period": "annual",
        "skills": ["ASME", "NDE", "ITP", "weld inspection"],
        "certifications": ["AWS CWI"],
    },
    {
        "title": "Project Director - Transit",
        "org": "AtkinsRéalis",
        "region": "CA-QC",
        "location": "Montréal, QC",
        "overlay": "construction.project-director",
        "occupation_system": "NOC", "occupation_code": "00012",
        "seniority": "executive",
        "salary_low": 175000, "salary_high": 215000, "currency": "CAD", "period": "annual",
        "skills": ["P3", "transit", "stakeholder management", "MEP coordination"],
        "certifications": ["PEng", "PMP"],
    },
    {
        "title": "Senior Cost Controller",
        "org": "AtkinsRéalis",
        "region": "CA-ON",
        "location": "Toronto, ON",
        "overlay": "construction.cost-controller",
        "occupation_system": "NOC", "occupation_code": "11100",
        "seniority": "senior",
        "salary_low": 100000, "salary_high": 130000, "currency": "CAD", "period": "annual",
        "skills": ["EVM", "Primavera P6", "cost reporting"],
    },
    {
        "title": "Pipefitter (Red Seal)",
        "org": "Suncor Energy",
        "region": "CA-AB",
        "location": "Fort McMurray, AB",
        "overlay": "trades.pipefitter",
        "occupation_system": "NOC", "occupation_code": "72301",
        "seniority": "journeyman",
        "salary_low": 84000, "salary_high": 110000, "currency": "CAD", "period": "annual",
        "skills": ["pipe fabrication", "blueprint reading"],
        "certifications": ["Red Seal"],
    },
    {
        "title": "Project Manager - Pipeline",
        "org": "Kiewit Corporation",
        "region": "CA-AB",
        "location": "Edmonton, AB",
        "overlay": "construction.project-manager",
        "occupation_system": "NOC", "occupation_code": "70010",
        "seniority": "senior",
        "salary_low": 140000, "salary_high": 180000, "currency": "CAD", "period": "annual",
        "skills": ["pipeline", "stakeholder management", "execution"],
        "certifications": ["PMP"],
    },
    {
        "title": "Scheduler - Major Projects",
        "org": "Kiewit Corporation",
        "region": "US-TX",
        "location": "Houston, TX",
        "overlay": "construction.scheduler",
        "occupation_system": "SOC", "occupation_code": "13-1082",
        "seniority": "intermediate",
        "salary_low": 95000, "salary_high": 125000, "currency": "USD", "period": "annual",
        "skills": ["Primavera P6", "CPM scheduling"],
    },
    {
        "title": "Commissioning Manager - LNG",
        "org": "Bechtel Corporation",
        "region": "CA-BC",
        "location": "Kitimat, BC",
        "overlay": "energy.commissioning-manager",
        "occupation_system": "NOC", "occupation_code": "21300",
        "seniority": "senior",
        "salary_low": 160000, "salary_high": 200000, "currency": "CAD", "period": "annual",
        "skills": ["LNG", "systems completions", "loop checks", "commissioning"],
        "certifications": ["PEng"],
    },
]

PROJECTS: list[dict] = [
    {
        "name": "Trans Mountain Expansion - Edmonton Terminal",
        "project_type": "pipeline",
        "region": "CA-AB",
        "location": "Edmonton, AB",
        "capex_usd": 21_400_000_000,
        "peak_headcount": 7600,
        "construction_start": date(2019, 12, 3),
        "expected_completion": date(2026, 5, 1),
        "source": "TC Energy (announcement)",
    },
    {
        "name": "LNG Canada Phase 2",
        "project_type": "lng",
        "region": "CA-BC",
        "location": "Kitimat, BC",
        "capex_usd": 14_000_000_000,
        "peak_headcount": 4500,
        "announced_on": date(2024, 11, 1),
        "construction_start": date(2026, 9, 1),
        "expected_completion": date(2030, 6, 1),
        "source": "Shell / LNG Canada JV",
    },
    {
        "name": "Ontario Line - South Civil Package",
        "project_type": "transit",
        "region": "CA-ON",
        "location": "Toronto, ON",
        "capex_usd": 3_900_000_000,
        "peak_headcount": 2400,
        "construction_start": date(2022, 9, 1),
        "expected_completion": date(2031, 12, 1),
        "source": "Metrolinx (procurement)",
    },
]


def apply(db: Session) -> SeedDemoResult:
    org_by_name: dict[str, Organization] = {}
    orgs_added = 0
    for spec in ORGS:
        existing = db.execute(
            select(Organization).where(Organization.canonical_name == spec["canonical_name"])
        ).scalar_one_or_none()
        if existing is None:
            existing = Organization(**spec)
            db.add(existing)
            db.flush()
            orgs_added += 1
        org_by_name[spec["canonical_name"]] = existing

    postings_added = 0
    for spec in POSTINGS:
        org = org_by_name[spec["org"]]
        dedup_key = hashlib.sha256(
            f"demo:{spec['org']}:{spec['title']}:{spec['region']}".encode()
        ).hexdigest()
        existing = db.execute(
            select(Posting).where(Posting.dedup_key == dedup_key)
        ).scalar_one_or_none()
        if existing is not None:
            existing.last_seen_at = NOW
            existing.source_count = (existing.source_count or 1) + 1
            continue

        posting = Posting(
            organization_id=org.id,
            title=spec["title"],
            occupation_code=spec.get("occupation_code"),
            occupation_system=spec.get("occupation_system"),
            industrial_overlay_code=spec.get("overlay"),
            seniority=spec.get("seniority"),
            region_code=spec["region"],
            location_text=spec.get("location"),
            salary_low=Decimal(str(spec["salary_low"])) if spec.get("salary_low") else None,
            salary_high=Decimal(str(spec["salary_high"])) if spec.get("salary_high") else None,
            salary_currency=spec.get("currency"),
            salary_period=spec.get("period"),
            skills=spec.get("skills", []),
            certifications=spec.get("certifications", []),
            first_seen_at=NOW - timedelta(days=14),
            last_seen_at=NOW,
            is_active=True,
            source_count=1,
            dedup_key=dedup_key,
            confidence={"occupation": 0.95, "source": "seed-demo"},
        )
        db.add(posting)
        db.flush()

        # Mirror as a RawPosting for the "raw scrape records" count.
        raw_id = f"seed-{dedup_key[:16]}"
        existing_raw = db.execute(
            select(RawPosting).where(
                RawPosting.source == "seed-demo",
                RawPosting.source_posting_id == raw_id,
            )
        ).scalar_one_or_none()
        if existing_raw is None:
            db.add(
                RawPosting(
                    source="seed-demo",
                    source_posting_id=raw_id,
                    source_url=f"seed://{raw_id}",
                    raw_title=spec["title"],
                    company_raw=spec["org"],
                    location_raw=spec.get("location"),
                    posted_date=TODAY - timedelta(days=14),
                    html_hash=dedup_key,
                    scraped_at=NOW,
                    posting_id=posting.id,
                    extra={"seed": True},
                )
            )
        postings_added += 1

    comp_added = 0
    for spec in POSTINGS[:8]:
        org = org_by_name[spec["org"]]
        observed_on = TODAY - timedelta(days=30 + comp_added * 3)
        mid = (spec["salary_low"] + spec["salary_high"]) / 2
        existing_comp = db.execute(
            select(CompensationRecord).where(
                CompensationRecord.industrial_overlay_code == spec["overlay"],
                CompensationRecord.region_code == spec["region"],
                CompensationRecord.observed_on == observed_on,
            )
        ).scalar_one_or_none()
        if existing_comp is not None:
            continue
        db.add(
            CompensationRecord(
                industrial_overlay_code=spec["overlay"],
                occupation_code=spec.get("occupation_code"),
                occupation_system=spec.get("occupation_system"),
                seniority=spec.get("seniority"),
                region_code=spec["region"],
                sector=org.sector_tags[0] if org.sector_tags else None,
                amount_low=Decimal(str(spec["salary_low"])),
                amount_mid=Decimal(str(mid)),
                amount_high=Decimal(str(spec["salary_high"])),
                currency=spec["currency"],
                period=spec["period"],
                source_type="placement_verified",
                confidence=Decimal("0.95"),
                observed_on=observed_on,
            )
        )
        comp_added += 1

    projects_added = 0
    for spec in PROJECTS:
        existing = db.execute(
            select(Project).where(Project.name == spec["name"])
        ).scalar_one_or_none()
        if existing is not None:
            continue
        db.add(
            Project(
                name=spec["name"],
                project_type=spec["project_type"],
                region_code=spec["region"],
                location_text=spec.get("location"),
                capex_usd=Decimal(str(spec["capex_usd"])) if spec.get("capex_usd") else None,
                estimated_peak_headcount=spec.get("peak_headcount"),
                announced_on=spec.get("announced_on"),
                construction_start_on=spec.get("construction_start"),
                expected_completion_on=spec.get("expected_completion"),
                source=spec.get("source"),
            )
        )
        projects_added += 1

    db.commit()

    canonical_total = int(db.scalar(select(func.count()).select_from(Posting)) or 0)
    raw_total = int(db.scalar(select(func.count()).select_from(RawPosting)) or 0)

    return SeedDemoResult(
        organizations_added=orgs_added,
        postings_added=postings_added,
        compensation_added=comp_added,
        projects_added=projects_added,
        canonical_postings_total=canonical_total,
        raw_postings_total=raw_total,
    )
