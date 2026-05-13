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

    def fetch(self, *, since: date | None = None) -> Iterable[dict[str, Any]]:
        # Full-table downloads are the path to use here; the time-series
        # API only exposes a subset. Concrete impl lands with the warehouse.
        return []


class QCEWConnector(BLSConnector):
    """Quarterly Census of Employment and Wages — quarterly."""

    def fetch(self, *, since: date | None = None) -> Iterable[dict[str, Any]]:
        # QCEW is best consumed via the flat-file bulk API:
        # https://data.bls.gov/cew/data/files/
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
