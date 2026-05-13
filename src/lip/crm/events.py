"""Event-log helpers for the recruiter CRM (§4.1).

Each function appends one row to ``recruiter_interaction`` and, where
relevant, materializes downstream artifacts (e.g. a placement creates a
``HiringEvent`` + ``CompensationRecord``). The CRM IS the event log.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from lip.models import CompensationRecord, HiringEvent, RecruiterInteraction


def log_event(
    db: Session,
    *,
    event_type: str,
    person_id: UUID | None = None,
    organization_id: UUID | None = None,
    recruiter: str | None = None,
    notes: str | None = None,
    payload: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> RecruiterInteraction:
    interaction = RecruiterInteraction(
        event_type=event_type,
        occurred_at=occurred_at or datetime.now(UTC),
        person_id=person_id,
        organization_id=organization_id,
        recruiter=recruiter,
        notes=notes,
        payload=payload or {},
    )
    db.add(interaction)
    db.flush()
    return interaction


def log_candidate_introduced(
    db: Session,
    *,
    person_id: UUID,
    organization_id: UUID,
    expected_compensation: float | None = None,
    recruiter: str | None = None,
) -> RecruiterInteraction:
    return log_event(
        db,
        event_type="candidate_introduced",
        person_id=person_id,
        organization_id=organization_id,
        recruiter=recruiter,
        payload={"expected_compensation": expected_compensation},
    )


def log_offer_extended(
    db: Session,
    *,
    person_id: UUID,
    organization_id: UUID,
    offered_amount: float,
    currency: str = "USD",
    period: str = "annual",
    recruiter: str | None = None,
) -> RecruiterInteraction:
    return log_event(
        db,
        event_type="offer_extended",
        person_id=person_id,
        organization_id=organization_id,
        recruiter=recruiter,
        payload={
            "offered_amount": offered_amount,
            "currency": currency,
            "period": period,
        },
    )


def log_candidate_declined(
    db: Session,
    *,
    person_id: UUID,
    organization_id: UUID,
    counter_amount: float | None = None,
    reason_code: str | None = None,
    recruiter: str | None = None,
) -> RecruiterInteraction:
    return log_event(
        db,
        event_type="candidate_declined",
        person_id=person_id,
        organization_id=organization_id,
        recruiter=recruiter,
        payload={
            "counter_amount": counter_amount,
            "reason_code": reason_code,
        },
    )


def log_placement_confirmed(
    db: Session,
    *,
    person_id: UUID,
    organization_id: UUID,
    start_date: date,
    base_compensation: float,
    currency: str = "USD",
    period: str = "annual",
    placement_type: str = "direct_hire",
    project_id: UUID | None = None,
    role_id: UUID | None = None,
    industrial_overlay_code: str | None = None,
    region_code: str | None = None,
    sector: str | None = None,
    source_channel: str | None = None,
    recruiter: str | None = None,
) -> tuple[RecruiterInteraction, HiringEvent, CompensationRecord]:
    """Create the canonical record of a closed hire — the gold asset."""
    interaction = log_event(
        db,
        event_type="placement_confirmed",
        person_id=person_id,
        organization_id=organization_id,
        recruiter=recruiter,
        payload={"start_date": start_date.isoformat()},
    )
    hiring_event = HiringEvent(
        person_id=person_id,
        organization_id=organization_id,
        role_id=role_id,
        project_id=project_id,
        placement_type=placement_type,
        start_date=start_date,
        source_channel=source_channel,
    )
    db.add(hiring_event)
    db.flush()
    comp = CompensationRecord(
        hiring_event_id=hiring_event.id,
        industrial_overlay_code=industrial_overlay_code,
        region_code=region_code,
        sector=sector,
        amount_mid=Decimal(base_compensation),
        currency=currency,
        period=period,
        source_type="placement_verified",
        confidence=Decimal("1.00"),
        observed_on=start_date,
    )
    db.add(comp)
    db.flush()
    return interaction, hiring_event, comp


def log_early_departure(
    db: Session,
    *,
    hiring_event_id: UUID,
    end_date: date,
    reason: str | None,
    person_id: UUID,
    organization_id: UUID,
    recruiter: str | None = None,
) -> RecruiterInteraction:
    he = db.get(HiringEvent, hiring_event_id)
    if he is not None:
        he.end_date = end_date
        he.early_departure_reason = reason
    return log_event(
        db,
        event_type="early_departure",
        person_id=person_id,
        organization_id=organization_id,
        recruiter=recruiter,
        payload={"hiring_event_id": str(hiring_event_id), "reason": reason},
    )


def log_client_engaged(
    db: Session,
    *,
    organization_id: UUID,
    notes: str | None = None,
    recruiter: str | None = None,
) -> RecruiterInteraction:
    return log_event(
        db,
        event_type="client_engaged",
        organization_id=organization_id,
        recruiter=recruiter,
        notes=notes,
    )
