"""Statistics Canada connectors — LFS, SEPH (§3).

StatCan's Web Data Service (WDS) is the canonical access point:
  https://www.statcan.gc.ca/en/developers/wds
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

WDS_BASE = "https://www150.statcan.gc.ca/t1/wds/rest"


class StatCanConnector:
    def __init__(self) -> None:
        self._client = httpx.Client(timeout=60.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
    def get_cube(self, pid: str) -> dict[str, Any]:
        resp = self._client.post(
            f"{WDS_BASE}/getCubeMetadata", json=[{"productId": pid}]
        )
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
    def get_data_from_vectors(self, vector_ids: list[int], n_periods: int) -> dict[str, Any]:
        body = [{"vectorId": v, "latestN": n_periods} for v in vector_ids]
        resp = self._client.post(
            f"{WDS_BASE}/getDataFromVectorsAndLatestNPeriods", json=body
        )
        resp.raise_for_status()
        return resp.json()


class LFSConnector(StatCanConnector):
    """Labour Force Survey - employment by NOC x province."""

    PID_EMPLOYMENT_BY_NOC = "14100023"  # Employment by NOC, monthly

    def fetch(self, *, since: date | None = None) -> Iterable[dict[str, Any]]:
        # Concrete vector list resolved against cube metadata on first run.
        return []


class SEPHConnector(StatCanConnector):
    """Survey of Employment, Payrolls and Hours — earnings by industry."""

    PID_EARNINGS_BY_NAICS = "14100204"

    def fetch(self, *, since: date | None = None) -> Iterable[dict[str, Any]]:
        return []
