"""GET /v1/projects/* — project registry and project-linked labor demand."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from lip.api.schemas import ProjectLaborDemand, ProjectOut
from lip.db import get_db
from lip.models import Project

router = APIRouter()


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: UUID, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.get("/{project_id}/labor-demand", response_model=ProjectLaborDemand)
def project_labor_demand(
    project_id: UUID, db: Session = Depends(get_db)
) -> ProjectLaborDemand:
    """Aggregate labor demand for a project.

    Body lands with Phase 6 once project→contractor→posting joins are
    instrumented. Returns an empty timeline until then.
    """
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    return ProjectLaborDemand(
        project_id=project_id, timeline=[], peak_demand_by_occupation={}
    )
