"""Recruiter CRM events — the proprietary data layer (§4.1)."""

from lip.crm.events import (
    log_candidate_declined,
    log_candidate_introduced,
    log_client_engaged,
    log_early_departure,
    log_event,
    log_offer_extended,
    log_placement_confirmed,
)

__all__ = [
    "log_candidate_declined",
    "log_candidate_introduced",
    "log_client_engaged",
    "log_early_departure",
    "log_event",
    "log_offer_extended",
    "log_placement_confirmed",
]
