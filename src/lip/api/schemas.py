"""Pydantic response/request schemas for the v1 API."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PostingOut(ORMModel):
    id: UUID
    title: str
    organization_id: UUID | None = None
    occupation_code: str | None = None
    occupation_system: str | None = None
    industrial_overlay_code: str | None = None
    seniority: str | None = None
    region_code: str | None = None
    location_text: str | None = None
    salary_low: float | None = None
    salary_high: float | None = None
    salary_currency: str | None = None
    salary_period: str | None = None
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    first_seen_at: datetime
    last_seen_at: datetime
    is_active: bool
    source_count: int


class CompensationStats(BaseModel):
    occupation: str
    region: str | None
    n_observations: int
    percentiles: dict[str, float]
    currency: str
    period: str
    source_mix: dict[str, int]


class LaborSupplyMetric(BaseModel):
    occupation_code: str
    region_code: str
    employment: int | None = None
    projected_change_pct: float | None = None
    shortage_indicator: float | None = None
    as_of: date


class MobilityEdge(BaseModel):
    from_sector: str
    to_sector: str
    region_code: str
    n_transitions: int
    median_tenure_months: float | None = None
    window_months: int


class OrganizationOut(ORMModel):
    id: UUID
    canonical_name: str
    sector_tags: list[str] = Field(default_factory=list)
    naics_code: str | None = None
    headcount_estimate: int | None = None
    operating_regions: list[str] = Field(default_factory=list)
    is_recruiter_client: bool


class OrgHiringActivity(BaseModel):
    organization_id: UUID
    window_days: int
    active_postings: int
    new_postings: int
    expired_postings: int
    top_occupations: list[dict]


class ProjectOut(ORMModel):
    id: UUID
    name: str
    project_type: str
    region_code: str | None = None
    location_text: str | None = None
    capex_usd: float | None = None
    estimated_peak_headcount: int | None = None
    announced_on: date | None = None
    construction_start_on: date | None = None
    expected_completion_on: date | None = None


class ProjectLaborDemand(BaseModel):
    project_id: UUID
    timeline: list[dict]
    peak_demand_by_occupation: dict[str, int]


class PersonCareerNode(BaseModel):
    role_id: UUID
    organization_id: UUID
    organization_name: str
    title: str
    occupation_code: str | None = None
    started_on: date
    ended_on: date | None = None


class PersonCareerGraph(BaseModel):
    person_id: UUID
    timeline: list[PersonCareerNode]
