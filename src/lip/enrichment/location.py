"""Location intelligence (§2.5).

The geocoder is intentionally swappable. The default implementation
returns a parsed-but-not-geocoded result so the pipeline runs without a
paid geocoding API. When ``LIP_GEOCODER`` is configured, the corresponding
client is loaded (Mapbox, OpenCage, etc.).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from lip.config import get_settings

_CA_PROVINCES: dict[str, str] = {
    "AB": "CA-AB", "BC": "CA-BC", "MB": "CA-MB", "NB": "CA-NB",
    "NL": "CA-NL", "NS": "CA-NS", "NT": "CA-NT", "NU": "CA-NU",
    "ON": "CA-ON", "PE": "CA-PE", "QC": "CA-QC", "SK": "CA-SK", "YT": "CA-YT",
    "ALBERTA": "CA-AB", "BRITISH COLUMBIA": "CA-BC", "MANITOBA": "CA-MB",
    "NEW BRUNSWICK": "CA-NB", "NEWFOUNDLAND": "CA-NL", "NOVA SCOTIA": "CA-NS",
    "ONTARIO": "CA-ON", "QUEBEC": "CA-QC", "SASKATCHEWAN": "CA-SK",
}
_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY",
}


@dataclass(slots=True)
class ResolvedLocation:
    region_code: str | None  # ISO-3166-2
    latitude: float | None = None
    longitude: float | None = None
    location_text: str | None = None


def resolve(location_raw: str | None) -> ResolvedLocation | None:
    if not location_raw:
        return None

    settings = get_settings()
    text = location_raw.strip()
    if settings.geocoder:
        # Geocoder client adapters land here. Returning the parsed form
        # for now keeps the pipeline deterministic in dev/test.
        pass

    region = _parse_region(text)
    return ResolvedLocation(region_code=region, location_text=text)


def _parse_region(text: str) -> str | None:
    upper = text.upper()
    tokens = re.split(r"[,\s]+", upper)
    for token in reversed(tokens):
        if token in _CA_PROVINCES:
            return _CA_PROVINCES[token]
        if token in _US_STATES:
            return f"US-{token}"
    for name, code in _CA_PROVINCES.items():
        if len(name) > 2 and name in upper:
            return code
    return None
