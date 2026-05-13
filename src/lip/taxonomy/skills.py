"""Proprietary industrial skills taxonomy seed (§2.2).

Each entry maps a canonical name to a tuple of common aliases / surface
forms found in postings. The set is intentionally small — production
runs add to it from extraction-failure review per §6.1.
"""

from __future__ import annotations

from typing import Final

TECHNICAL_SKILLS: Final[dict[str, tuple[str, ...]]] = {
    "structural welding": ("structural welding", "structural welder"),
    "b-pressure welding": ("b pressure welding", "b-pressure welding"),
    "concrete formwork": ("concrete formwork", "formwork"),
    "rebar placement": ("rebar placement", "rebar tying"),
    "crane rigging": ("crane rigging", "rigging"),
    "boiler operation": ("boiler operation",),
    "pipe fitting": ("pipe fitting", "pipefitting"),
    "industrial electrical": ("industrial electrical", "industrial wiring"),
    "instrumentation": ("instrumentation", "instrumentation and controls"),
    "scheduling p6": ("primavera p6", "p6 scheduling"),
    "estimating": ("cost estimating", "construction estimating"),
    "commissioning": ("commissioning", "cx"),
    "shutdown turnaround": ("shutdown turnaround", "turnaround planning"),
    "reliability engineering": ("reliability engineering", "rcm"),
    "structural steel erection": ("steel erection", "structural steel erection"),
    "predictive maintenance": ("predictive maintenance", "pdm"),
}

SOFTWARE_SKILLS: Final[dict[str, tuple[str, ...]]] = {
    "Primavera P6": ("primavera p6", "oracle primavera"),
    "MS Project": ("ms project", "microsoft project"),
    "AutoCAD": ("autocad",),
    "Revit": ("revit", "autodesk revit"),
    "Civil 3D": ("civil 3d", "civil3d"),
    "SAP PM": ("sap pm",),
    "Maximo": ("ibm maximo", "maximo"),
    "Procore": ("procore",),
    "Bluebeam Revu": ("bluebeam", "bluebeam revu"),
    "Navisworks": ("navisworks",),
    "Aspen HYSYS": ("hysys", "aspen hysys"),
    "PHA-Pro": ("pha pro", "pha-pro"),
}

CERTIFICATIONS: Final[dict[str, tuple[str, ...]]] = {
    "Red Seal": ("red seal",),
    "P.Eng": ("p.eng", "professional engineer", "p eng"),
    "CET": ("c.e.t.", "certified engineering technologist"),
    "LEED AP": ("leed ap", "leed accredited professional"),
    "PMP": ("pmp",),
    "GSC": ("gsc gold seal", "gold seal certified"),
    "NCCER": ("nccer",),
    "OSHA 30": ("osha 30",),
    "PSM": ("process safety management", "psm"),
    "HAZWOPER": ("hazwoper",),
    "ISO 55001": ("iso 55001",),
}
