"""BLS connectors — QCEW, OEWS, JOLTS (§3).

BLS public APIs:
  - Time-series API v2 (auth optional but rate-limited free tier)
  - Bulk flat files (preferred for QCEW / OEWS — full table downloads)
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from lip.config import get_settings

BLS_TIMESERIES_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


class BLSConnector:
    """Minimal client over BLS time-series API.

    Subclasses (``QCEWConnector``, ``OEWSConnector``, ``JOLTSConnector``)
    supply the relevant series IDs. The bulk flat-file path is preferred
    for full historical loads and lives under ``flat_files.py`` once the
    warehouse target is wired up.
    """

    name: str = ""
    description: str = ""
    dataset_label: str = ""
    update_frequency: str = ""
    granularity: str = ""
    status: str = "scaffolded"
    country: str = "US"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = httpx.Client(timeout=60.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
    def fetch_series(
        self, series_ids: list[str], start_year: int, end_year: int
    ) -> dict[str, Any]:
        payload = {
            "seriesid": series_ids,
            "startyear": str(start_year),
            "endyear": str(end_year),
        }
        if self._settings.bls_api_key:
            payload["registrationkey"] = self._settings.bls_api_key
        resp = self._client.post(BLS_TIMESERIES_URL, json=payload)
        resp.raise_for_status()
        return resp.json()


class JOLTSConnector(BLSConnector):
    """Job Openings and Labor Turnover Survey."""

    name = "bls_jolts"
    description = "Job openings, hires, and separations by industry (US)."
    dataset_label = "bls_jolts"
    update_frequency = "monthly"
    granularity = "industry / national"

    # Industry-level series IDs; full list loaded from BLS website during ETL.
    DEFAULT_SERIES: tuple[str, ...] = (
        "JTU2300000000000JOL",  # Construction job openings, US total, level (000)
        "JTU2300000000000HIL",  # Construction hires, US total, level (000)
        "JTU2300000000000QUL",  # Construction quits, US total, level (000)
    )

    def fetch(self, *, since: date | None = None) -> Iterable[dict[str, Any]]:
        end_year = (since or date.today()).year
        start_year = end_year - 1
        return _flatten(self.fetch_series(list(self.DEFAULT_SERIES), start_year, end_year))


class OEWSConnector(BLSConnector):
    """Occupational Employment and Wage Statistics — annual."""

    name = "bls_oews"
    description = "Occupational employment and wage statistics by MSA (US)."
    dataset_label = "bls_oews"
    update_frequency = "annual"
    granularity = "MSA"

    def fetch(self, *, since: date | None = None) -> Iterable[dict[str, Any]]:
        return []


class QCEWConnector(BLSConnector):
    """Quarterly Census of Employment and Wages — quarterly."""

    name = "bls_qcew"
    description = "Quarterly census of employment and wages by NAICS / county (US)."
    dataset_label = "bls_qcew"
    update_frequency = "quarterly"
    granularity = "county"

    def fetch(self, *, since: date | None = None) -> Iterable[dict[str, Any]]:
        return []


def _flatten(payload: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for series in payload.get("Results", {}).get("series", []):
        series_id = series["seriesID"]
        for obs in series.get("data", []):
            out.append({
                "series_id": series_id,
                "year": int(obs["year"]),
                "period": obs["period"],
                "value": float(obs["value"]),
            })
    return out
