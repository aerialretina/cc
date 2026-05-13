"""Spider registry — map source_name → spider class."""

from __future__ import annotations

from lip.scraping.base import Spider
from lip.scraping.sources.adecco import (
    AdeccoCanadaSpider,
    AdeccoUSSpider,
    AkkodisSpider,
)
from lip.scraping.sources.eluta import ElutaSpider
from lip.scraping.sources.greenhouse import StantecGreenhouseSpider, WSPGreenhouseSpider
from lip.scraping.sources.job_bank_canada import JobBankCanadaSpider
from lip.scraping.sources.kelly import KellyCanadaSpider, KellyUSSpider
from lip.scraping.sources.lever import ChandosLeverSpider
from lip.scraping.sources.randstad import (
    RandstadCanadaSpider,
    RandstadUSSpider,
)
from lip.scraping.sources.tier1_careers import (
    AeconCareersSpider,
    BrucePowerCareersSpider,
    EllisDonCareersSpider,
    EnbridgeCareersSpider,
    OPGCareersSpider,
    PCLCareersSpider,
    SuncorCareersSpider,
    TCEnergyCareersSpider,
)
from lip.scraping.sources.vertical_boards import (
    ConstructionJobsCanadaSpider,
    ConstructionJobSiteCASpider,
    EnergyJobShopSpider,
    IHireConstructionSpider,
    IndeedCanadaSpider,
    OilAndGasJobSearchSpider,
    SPEJobBoardSpider,
)
from lip.scraping.sources.workbc import WorkBCSpider
from lip.scraping.sources.workday import (
    AtkinsRealisWorkdaySpider,
    CamecoWorkdaySpider,
    EnbridgeWorkdaySpider,
    HydroOneWorkdaySpider,
    OPGWorkdaySpider,
    PCLWorkdaySpider,
    SuncorWorkdaySpider,
    TeckWorkdaySpider,
)

_CLASSES: tuple[type[Spider], ...] = (
    # Tier 1 — ATS APIs (highest signal: stable JSON endpoints, no bot challenge)
    # Workday
    PCLWorkdaySpider, OPGWorkdaySpider, SuncorWorkdaySpider,
    CamecoWorkdaySpider, EnbridgeWorkdaySpider, AtkinsRealisWorkdaySpider,
    TeckWorkdaySpider, HydroOneWorkdaySpider,
    # Greenhouse
    StantecGreenhouseSpider, WSPGreenhouseSpider,
    # Lever
    ChandosLeverSpider,
    # Tier 1 — direct company careers (HTML scrape fallback)
    PCLCareersSpider, AeconCareersSpider, EllisDonCareersSpider,
    SuncorCareersSpider, TCEnergyCareersSpider, EnbridgeCareersSpider,
    OPGCareersSpider, BrucePowerCareersSpider,
    # Tier 2 — vertical / niche boards
    ConstructionJobsCanadaSpider, ConstructionJobSiteCASpider,
    EnergyJobShopSpider, OilAndGasJobSearchSpider, SPEJobBoardSpider,
    IHireConstructionSpider,
    # Tier 2/3 — provincial / national government boards
    JobBankCanadaSpider, WorkBCSpider,
    # Tier 3 — staffing agencies (Randstad / Kelly / Adecco / Akkodis)
    RandstadCanadaSpider, RandstadUSSpider,
    KellyCanadaSpider, KellyUSSpider,
    AdeccoCanadaSpider, AdeccoUSSpider, AkkodisSpider,
    # Tier 3 — general boards / aggregators
    ElutaSpider, IndeedCanadaSpider,
)

_REGISTRY: dict[str, type[Spider]] = {cls.source_name: cls for cls in _CLASSES}


def get_spider(source_name: str) -> type[Spider]:
    try:
        return _REGISTRY[source_name]
    except KeyError as exc:
        raise KeyError(f"unknown spider: {source_name}") from exc


def list_spiders() -> list[str]:
    return sorted(_REGISTRY.keys())


def all_spider_classes() -> list[type[Spider]]:
    """Return all registered spider classes (for the /ui/sources page)."""
    return list(_CLASSES)
