"""GET /v1/persons/{person_id}/career-graph — internal-only career history."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from lip.api.schemas import PersonCareerGraph, PersonCareerNode
from lip.db import get_db
from lip.models import Person, Role

router = APIRouter()


@router.get("/{person_id}/career-graph", response_model=PersonCareerGraph)
def career_graph(person_id: UUID, db: Session = Depends(get_db)) -> PersonCareerGraph:
    if db.get(Person, person_id) is None:
        raise HTTPException(status_code=404, detail="person not found")

    roles = db.scalars(
        select(Role)
        .options(joinedload(Role.organization))
        .where(Role.person_id == person_id)
        .order_by(Role.started_on.asc())
    ).all()

    timeline = [
        PersonCareerNode(
            role_id=r.id,
            organization_id=r.organization_id,
            organization_name=r.organization.canonical_name,
            title=r.title_raw,
            occupation_code=r.occupation_code,
            started_on=r.started_on,
            ended_on=r.ended_on,
        )
        for r in roles
    ]
    return PersonCareerGraph(person_id=person_id, timeline=timeline)
