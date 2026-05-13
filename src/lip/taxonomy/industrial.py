"""Industrial overlay taxonomy (§2.1).

Codes are stable, human-readable strings. Each entry carries keywords
used by the rule-based occupation classifier; once the ML classifier is
trained on labeled placement history, keywords become an additional
feature rather than the sole signal.
"""

from __future__ import annotations

from typing import Final, TypedDict


class OverlayEntry(TypedDict):
    label: str
    family: str  # "construction" | "energy" | "industrial" | "trades"
    keywords: tuple[str, ...]


INDUSTRIAL_OVERLAY: Final[dict[str, OverlayEntry]] = {
    # ---- Construction ----
    "con.project_executive": {
        "label": "Project Executive",
        "family": "construction",
        "keywords": ("project executive", "px"),
    },
    "con.project_manager": {
        "label": "Project Manager (Construction)",
        "family": "construction",
        "keywords": ("project manager", "construction manager", "pm "),
    },
    "con.superintendent": {
        "label": "Construction Superintendent",
        "family": "construction",
        "keywords": ("superintendent", "site super"),
    },
    "con.estimator": {
        "label": "Estimator",
        "family": "construction",
        "keywords": ("estimator", "preconstruction"),
    },
    "con.scheduler": {
        "label": "Scheduler",
        "family": "construction",
        "keywords": ("scheduler", "p6 scheduler", "primavera scheduler"),
    },
    "con.owners_rep": {
        "label": "Owner's Representative",
        "family": "construction",
        "keywords": ("owner's rep", "owners rep", "owner representative"),
    },
    "con.qa_qc_manager": {
        "label": "QA/QC Manager",
        "family": "construction",
        "keywords": ("qa/qc", "quality manager", "qaqc"),
    },
    "con.commissioning_manager": {
        "label": "Commissioning Manager",
        "family": "construction",
        "keywords": ("commissioning manager", "cx manager"),
    },

    # ---- Energy ----
    "en.completions_engineer": {
        "label": "Completions Engineer",
        "family": "energy",
        "keywords": ("completions engineer",),
    },
    "en.reservoir_engineer": {
        "label": "Reservoir Engineer",
        "family": "energy",
        "keywords": ("reservoir engineer",),
    },
    "en.facilities_engineer": {
        "label": "Facilities Engineer",
        "family": "energy",
        "keywords": ("facilities engineer",),
    },
    "en.plant_manager": {
        "label": "Plant Manager",
        "family": "energy",
        "keywords": ("plant manager",),
    },
    "en.epcm_pm": {
        "label": "EPCM Project Manager",
        "family": "energy",
        "keywords": ("epcm project manager", "epcm pm"),
    },

    # ---- Industrial ----
    "ind.maintenance_super": {
        "label": "Maintenance Superintendent",
        "family": "industrial",
        "keywords": ("maintenance superintendent",),
    },
    "ind.reliability_engineer": {
        "label": "Reliability Engineer",
        "family": "industrial",
        "keywords": ("reliability engineer",),
    },
    "ind.shutdown_coordinator": {
        "label": "Shutdown Coordinator",
        "family": "industrial",
        "keywords": ("shutdown coordinator", "turnaround coordinator"),
    },

    # ---- Skilled Trades (Red Seal subset) ----
    "tr.pipefitter": {
        "label": "Pipefitter (Red Seal)",
        "family": "trades",
        "keywords": ("pipefitter", "steamfitter"),
    },
    "tr.boilermaker": {
        "label": "Boilermaker (Red Seal)",
        "family": "trades",
        "keywords": ("boilermaker",),
    },
    "tr.ironworker": {
        "label": "Ironworker (Red Seal)",
        "family": "trades",
        "keywords": ("ironworker", "iron worker"),
    },
    "tr.electrician": {
        "label": "Construction Electrician (Red Seal)",
        "family": "trades",
        "keywords": ("electrician", "industrial electrician"),
    },
    "tr.millwright": {
        "label": "Industrial Mechanic / Millwright (Red Seal)",
        "family": "trades",
        "keywords": ("millwright", "industrial mechanic"),
    },
    "tr.welder": {
        "label": "Welder (Red Seal)",
        "family": "trades",
        "keywords": ("welder", "b pressure", "structural welder"),
    },
}


def family_of(code: str | None) -> str | None:
    if code is None:
        return None
    entry = INDUSTRIAL_OVERLAY.get(code)
    return entry["family"] if entry else None
