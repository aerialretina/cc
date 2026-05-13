"""Statistics Canada connectors (§3).

StatCan's Web Data Service (WDS) is the canonical access point:
  https://www150.statcan.gc.ca/t1/wds/rest

Each connector class targets one statistical product (PID = Product ID).
At Phase 0 the classes carry metadata and a real URL builder; live
``fetch()`` lands once the WDS pipelines are wired up. The metadata
drives the ``/ui/sources`` coverage page and the
``/v1/labor-supply`` overlay.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

WDS_BASE = "https://www150.statcan.gc.ca/t1/wds/rest"


class StatCanConnector:
    """Base — shared HTTP client + WDS endpoint helpers."""

    name: str = ""
    description: str = ""
    pid: str = ""
    dataset_label: str = ""  # what column the seed/api populates (LMI source field)
    update_frequency: str = ""  # "monthly" / "quarterly" / "annual" / "5y"
    status: str = "scaffolded"  # "scaffolded" | "live"
    granularity: str = ""  # "Canada" / "province" / "CD" / "CSD" / "ER"
    country: str = "CA"

    def __init__(self) -> None:
        self._client = httpx.Client(timeout=60.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
    def get_cube_metadata(self) -> dict[str, Any]:
        resp = self._client.post(
            f"{WDS_BASE}/getCubeMetadata", json=[{"productId": self.pid}]
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

    def fetch(self, *, since: date | None = None) -> Iterable[dict[str, Any]]:
        """Yield normalized records ready to upsert into lmi_snapshot.

        Default impl returns an empty list; override per dataset.
        """
        return []


# ---------------------------------------------------------------------------
# Labour Force Survey (LFS)
# ---------------------------------------------------------------------------

class LFSEmploymentByNOCByERConnector(StatCanConnector):
    name = "statcan_lfs_employment_noc_er"
    description = "Annual employment by NOC, class of worker, Economic Region."
    pid = "14100296"
    dataset_label = "statcan_lfs"
    update_frequency = "annual"
    granularity = "Economic Region"


class LFSEmploymentByIndustryByERConnector(StatCanConnector):
    name = "statcan_lfs_employment_naics_er"
    description = "Annual employment by industry (NAICS), Economic Region."
    pid = "14100098"
    dataset_label = "statcan_lfs"
    update_frequency = "annual"
    granularity = "Economic Region"


class LFSEarningsByOccupationByERConnector(StatCanConnector):
    name = "statcan_lfs_earnings_occ_er"
    description = (
        "Annual employment / earnings (two-year rolling averages) "
        "by occupation, employees, Economic Region."
    )
    pid = "14100417"
    dataset_label = "statcan_lfs"
    update_frequency = "annual"
    granularity = "Economic Region"


# ---------------------------------------------------------------------------
# Survey of Employment, Payrolls and Hours (SEPH)
# ---------------------------------------------------------------------------

class SEPHAnnualEmploymentByIndustryConnector(StatCanConnector):
    name = "statcan_seph_annual_employment"
    description = "Annual employment by industry, province / territory."
    pid = "14100222"
    dataset_label = "statcan_seph"
    update_frequency = "annual"
    granularity = "province"


class SEPHAnnualWeeklyEarningsConnector(StatCanConnector):
    name = "statcan_seph_annual_earnings"
    description = "Annual weekly earnings by industry, province / territory."
    pid = "14100204"
    dataset_label = "statcan_seph"
    update_frequency = "annual"
    granularity = "province"


class SEPHMonthlyEmploymentByIndustryConnector(StatCanConnector):
    name = "statcan_seph_monthly_employment"
    description = "Monthly employment by industry, province / territory."
    pid = "14100223"
    dataset_label = "statcan_seph"
    update_frequency = "monthly"
    granularity = "province"


class SEPHMonthlyWeeklyEarningsConnector(StatCanConnector):
    name = "statcan_seph_monthly_earnings"
    description = "Monthly weekly earnings by industry, province / territory."
    pid = "14100205"
    dataset_label = "statcan_seph"
    update_frequency = "monthly"
    granularity = "province"


# ---------------------------------------------------------------------------
# Canadian Business Patterns (CBP)
# ---------------------------------------------------------------------------

class CBPEstablishmentCountsConnector(StatCanConnector):
    name = "statcan_cbp_establishments"
    description = "Establishment counts by industry (NAICS), CSD."
    pid = "33100037"
    dataset_label = "statcan_cbp"
    update_frequency = "semi-annual"
    granularity = "CSD"


class CBPLocationCountsConnector(StatCanConnector):
    name = "statcan_cbp_locations"
    description = "Location counts by industry (NAICS), CSD."
    pid = "33100038"
    dataset_label = "statcan_cbp"
    update_frequency = "semi-annual"
    granularity = "CSD"


# ---------------------------------------------------------------------------
# Census + National Household Survey (2001, 2006, 2011, 2016, 2021)
# ---------------------------------------------------------------------------

class CensusWorkplaceEarningsByCDConnector(StatCanConnector):
    name = "statcan_census_workplace_earnings_cd"
    description = (
        "Workplace-based: earnings by class of worker, industry, "
        "Census Division (2001 / 2006 / 2011 / 2016 / 2021)."
    )
    pid = "98100450"
    dataset_label = "statcan_census"
    update_frequency = "5y"
    granularity = "CD"


class CensusWorkplaceEmploymentByCSDConnector(StatCanConnector):
    name = "statcan_census_workplace_employment_csd"
    description = (
        "Workplace-based: employment by class of worker, industry, CSD "
        "(2001 / 2006 / 2011 / 2016 / 2021)."
    )
    pid = "98100451"
    dataset_label = "statcan_census"
    update_frequency = "5y"
    granularity = "CSD"


class CensusWorkplaceEmploymentByOccProvinceConnector(StatCanConnector):
    name = "statcan_census_workplace_employment_occ_prov"
    description = (
        "Workplace-based: employment by class of worker, industry, "
        "occupation, province."
    )
    pid = "98100452"
    dataset_label = "statcan_census"
    update_frequency = "5y"
    granularity = "province"


# ---------------------------------------------------------------------------
# Canadian Occupational Projection System (COPS)
# ---------------------------------------------------------------------------

class COPSIndustryProjectionsConnector(StatCanConnector):
    name = "esdc_cops_industry"
    description = "Industry employment projections, Canada (ESDC / COPS)."
    pid = "cops:industry"
    dataset_label = "esdc_cops"
    update_frequency = "biennial"
    granularity = "Canada"


class COPSOccupationProjectionsConnector(StatCanConnector):
    name = "esdc_cops_occupation"
    description = "Occupation employment projections, Canada (ESDC / COPS)."
    pid = "cops:occupation"
    dataset_label = "esdc_cops"
    update_frequency = "biennial"
    granularity = "Canada"


# ---------------------------------------------------------------------------
# Demographics
# ---------------------------------------------------------------------------

class DemographicsHistoricAgeGenderConnector(StatCanConnector):
    name = "statcan_demo_historic_age_gender_cd"
    description = "Historic age / gender, Census Division (17-10-0084-01)."
    pid = "17100084"
    dataset_label = "statcan_demo"
    update_frequency = "annual"
    granularity = "CD"


class DemographicsHistoricPopulationComponentsConnector(StatCanConnector):
    name = "statcan_demo_historic_population_components_cd"
    description = "Historic population components, Census Division (17-10-0085-01)."
    pid = "17100085"
    dataset_label = "statcan_demo"
    update_frequency = "annual"
    granularity = "CD"


class DemographicsProjectedAgeGenderConnector(StatCanConnector):
    name = "statcan_demo_projected_age_gender_prov"
    description = "Projected age / gender, province / territory (17-10-0057-01)."
    pid = "17100057"
    dataset_label = "statcan_demo"
    update_frequency = "biennial"
    granularity = "province"


class DemographicsFertilityRatesConnector(StatCanConnector):
    name = "statcan_demo_fertility"
    description = "Fertility rates (13-10-0418-01)."
    pid = "13100418"
    dataset_label = "statcan_demo"
    update_frequency = "annual"
    granularity = "Canada"


class DemographicsDeathRatesConnector(StatCanConnector):
    name = "statcan_demo_deaths"
    description = "Death rates (13-10-0710-01)."
    pid = "13100710"
    dataset_label = "statcan_demo"
    update_frequency = "annual"
    granularity = "Canada"


# ---------------------------------------------------------------------------
# Postsecondary Student Information System (PSIS)
# ---------------------------------------------------------------------------

class PSISEnrollmentsConnector(StatCanConnector):
    name = "statcan_psis_enrollments"
    description = (
        "Postsecondary enrollments and completions by award level, "
        "program, institution, CSD (PSIS)."
    )
    pid = "37100011"
    dataset_label = "statcan_psis"
    update_frequency = "annual"
    granularity = "CSD"


__all__ = [  # noqa: RUF022 — grouped by data source, not alphabetical
    "StatCanConnector",
    # LFS
    "LFSEmploymentByNOCByERConnector",
    "LFSEmploymentByIndustryByERConnector",
    "LFSEarningsByOccupationByERConnector",
    # SEPH
    "SEPHAnnualEmploymentByIndustryConnector",
    "SEPHAnnualWeeklyEarningsConnector",
    "SEPHMonthlyEmploymentByIndustryConnector",
    "SEPHMonthlyWeeklyEarningsConnector",
    # CBP
    "CBPEstablishmentCountsConnector",
    "CBPLocationCountsConnector",
    # Census
    "CensusWorkplaceEarningsByCDConnector",
    "CensusWorkplaceEmploymentByCSDConnector",
    "CensusWorkplaceEmploymentByOccProvinceConnector",
    # COPS
    "COPSIndustryProjectionsConnector",
    "COPSOccupationProjectionsConnector",
    # Demographics
    "DemographicsHistoricAgeGenderConnector",
    "DemographicsHistoricPopulationComponentsConnector",
    "DemographicsProjectedAgeGenderConnector",
    "DemographicsFertilityRatesConnector",
    "DemographicsDeathRatesConnector",
    # PSIS
    "PSISEnrollmentsConnector",
]
