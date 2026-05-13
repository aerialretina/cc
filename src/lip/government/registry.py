"""Government data-connector registry.

A single catalog of every external statistical source we plan to ingest,
keyed by ``name``. Drives the ``/ui/sources`` coverage page and gives
operators one place to see what's wired up vs scaffolded.
"""

from __future__ import annotations

from lip.government.bls import JOLTSConnector, OEWSConnector, QCEWConnector
from lip.government.statcan import (
    CBPEstablishmentCountsConnector,
    CBPLocationCountsConnector,
    CensusWorkplaceEarningsByCDConnector,
    CensusWorkplaceEmploymentByCSDConnector,
    CensusWorkplaceEmploymentByOccProvinceConnector,
    COPSIndustryProjectionsConnector,
    COPSOccupationProjectionsConnector,
    DemographicsDeathRatesConnector,
    DemographicsFertilityRatesConnector,
    DemographicsHistoricAgeGenderConnector,
    DemographicsHistoricPopulationComponentsConnector,
    DemographicsProjectedAgeGenderConnector,
    LFSEarningsByOccupationByERConnector,
    LFSEmploymentByIndustryByERConnector,
    LFSEmploymentByNOCByERConnector,
    PSISEnrollmentsConnector,
    SEPHAnnualEmploymentByIndustryConnector,
    SEPHAnnualWeeklyEarningsConnector,
    SEPHMonthlyEmploymentByIndustryConnector,
    SEPHMonthlyWeeklyEarningsConnector,
)

_CONNECTORS = (
    # ---- Statistics Canada ----
    # LFS
    LFSEmploymentByNOCByERConnector,
    LFSEmploymentByIndustryByERConnector,
    LFSEarningsByOccupationByERConnector,
    # SEPH
    SEPHAnnualEmploymentByIndustryConnector,
    SEPHAnnualWeeklyEarningsConnector,
    SEPHMonthlyEmploymentByIndustryConnector,
    SEPHMonthlyWeeklyEarningsConnector,
    # CBP
    CBPEstablishmentCountsConnector,
    CBPLocationCountsConnector,
    # Census + NHS
    CensusWorkplaceEarningsByCDConnector,
    CensusWorkplaceEmploymentByCSDConnector,
    CensusWorkplaceEmploymentByOccProvinceConnector,
    # COPS
    COPSIndustryProjectionsConnector,
    COPSOccupationProjectionsConnector,
    # Demographics
    DemographicsHistoricAgeGenderConnector,
    DemographicsHistoricPopulationComponentsConnector,
    DemographicsProjectedAgeGenderConnector,
    DemographicsFertilityRatesConnector,
    DemographicsDeathRatesConnector,
    # PSIS
    PSISEnrollmentsConnector,
    # ---- US BLS ----
    JOLTSConnector,
    OEWSConnector,
    QCEWConnector,
)


def all_connector_classes() -> list[type]:
    return list(_CONNECTORS)


def list_connectors() -> list[str]:
    return sorted(c.name for c in _CONNECTORS if getattr(c, "name", ""))
