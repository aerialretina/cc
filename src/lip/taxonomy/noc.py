"""NOC 2021 (National Occupational Classification, Canada).

The full TEER-coded set is loaded from StatCan's published table during
ETL. This module ships only the seed used by the rule-based classifier
and tests — actual classification consumes the full table from the DB.
"""

from __future__ import annotations

from typing import Final

# NOC code → (label, TEER, broad category).
NOC_SEED: Final[dict[str, tuple[str, int, str]]] = {
    "70010": ("Construction managers", 0, "Construction"),
    "72100": ("Machinists / machining and tooling inspectors", 2, "Trades"),
    "72200": ("Electricians (except industrial and power system)", 2, "Trades"),
    "72201": ("Industrial electricians", 2, "Trades"),
    "72300": ("Plumbers", 2, "Trades"),
    "72301": ("Steamfitters, pipefitters and sprinkler system installers", 2, "Trades"),
    "72400": ("Construction millwrights and industrial mechanics", 2, "Trades"),
    "72401": ("Heavy-duty equipment mechanics", 2, "Trades"),
    "72500": ("Crane operators", 2, "Trades"),
    "72600": ("Heavy equipment operators", 2, "Trades"),
    "73100": ("Concrete finishers", 3, "Trades"),
    "73101": ("Tilesetters", 3, "Trades"),
    "73102": ("Plasterers, drywall installers and lathers", 3, "Trades"),
    "73200": ("Residential / commercial installers and servicers", 3, "Trades"),
    "73300": ("Transport truck drivers", 3, "Trades"),
    "21300": ("Civil engineers", 1, "Engineering"),
    "21301": ("Mechanical engineers", 1, "Engineering"),
    "21310": ("Electrical and electronics engineers", 1, "Engineering"),
    "21320": ("Chemical engineers", 1, "Engineering"),
    "22301": ("Civil engineering technologists and technicians", 2, "Engineering"),
    "95100": ("Labourers in mineral and metal processing", 4, "Industrial"),
}
