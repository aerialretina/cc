"""Realistic Canadian industrial seed data for the UI.

This is the data the platform's UI exercises against in environments
where live spiders are unreachable. It mirrors the kind of work the
recruiting business places: industrial GCs, EPCs, energy producers,
pipeline operators, miners, and utilities across all Canadian
provinces, with credible salary ranges and named projects.

All upserts are keyed on a deterministic dedup hash so re-running
refreshes ``last_seen_at`` rather than duplicating.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lip.api.routes.admin import SeedDemoResult
from lip.models import (
    CompensationRecord,
    Organization,
    Posting,
    Project,
    RawPosting,
)

NOW = datetime.now(UTC)
TODAY = date.today()


def _o(name, aliases, sector_tags, naics, headcount, regions, **kw):
    return {
        "canonical_name": name,
        "aliases": aliases,
        "sector_tags": sector_tags,
        "naics_code": naics,
        "headcount_estimate": headcount,
        "operating_regions": regions,
        **kw,
    }


ORGS: list[dict] = [
    # ---- Canadian General Contractors / Construction Managers ----
    _o("PCL Construction Group", ["PCL Constructors", "PCL"], ["construction", "epc"], "236220", 5400,
       ["CA-AB", "CA-BC", "CA-ON", "CA-MB", "CA-SK", "US-CO", "US-CA"],
       website="https://www.pcl.com", careers_url="https://www.pcl.com/careers", enr_rank=7, is_recruiter_client=True),
    _o("EllisDon Corporation", ["EllisDon"], ["construction", "epc"], "236220", 4200,
       ["CA-ON", "CA-AB", "CA-BC", "CA-QC", "CA-NS"], website="https://www.ellisdon.com", is_recruiter_client=True),
    _o("Graham Construction", ["Graham"], ["construction"], "236220", 3000,
       ["CA-AB", "CA-BC", "CA-SK", "CA-ON"], website="https://www.grahambuilds.com", is_recruiter_client=True),
    _o("Bird Construction", ["Bird"], ["construction"], "236220", 5400,
       ["CA-ON", "CA-AB", "CA-NL", "CA-NS", "CA-NU"], website="https://www.bird.ca"),
    _o("Aecon Group", ["Aecon"], ["construction", "infrastructure"], "237310", 8800,
       ["CA-ON", "CA-AB", "CA-BC", "CA-QC"], website="https://www.aecon.com", is_recruiter_client=True),
    _o("Pomerleau", ["Pomerleau Inc."], ["construction"], "236220", 4500,
       ["CA-QC", "CA-ON", "CA-AB"], website="https://pomerleau.ca"),
    _o("Ledcor Group", ["Ledcor"], ["construction", "infrastructure"], "236220", 8000,
       ["CA-BC", "CA-AB", "CA-ON", "US-WA"], website="https://www.ledcor.com", is_recruiter_client=True),
    _o("Chandos Construction", ["Chandos"], ["construction"], "236220", 600,
       ["CA-AB", "CA-ON", "CA-BC"], website="https://chandos.com"),
    _o("Modern Niagara", ["Modern Niagara Group"], ["construction", "mep"], "238220", 2400,
       ["CA-ON", "CA-AB", "CA-BC", "CA-QC"], website="https://www.modernniagara.com"),
    _o("Maple Reinders", ["Maple Reinders Constructors"], ["construction"], "236210", 700,
       ["CA-ON", "CA-AB", "CA-BC"], website="https://www.maple.ca"),
    _o("Walsh Canada", ["Walsh Group", "Walsh Construction Canada"], ["construction"], "236220", 700,
       ["CA-ON", "CA-AB"], website="https://www.walshgroup.com"),
    _o("North American Construction Group", ["NACG", "North American Energy Partners"],
       ["construction", "mining"], "237310", 4000, ["CA-AB", "CA-BC", "US-WY"],
       website="https://nacg.ca", is_recruiter_client=True),
    _o("Aldridge Pipeline", ["Aldridge"], ["construction", "pipeline"], "237120", 400,
       ["CA-AB", "CA-BC", "CA-SK"], website="https://www.aldridge.com"),
    _o("Tarsus Building Group", ["Tarsus"], ["construction"], "236220", 200, ["CA-ON"]),
    _o("Bondfield Construction", ["Bondfield"], ["construction"], "236220", 1100, ["CA-ON"]),

    # ---- Engineering / EPC consultancies ----
    _o("Stantec", ["Stantec Inc."], ["engineering", "epc"], "541330", 32000,
       ["CA-AB", "CA-ON", "CA-BC", "CA-QC", "US-NY", "US-TX"], website="https://www.stantec.com", is_recruiter_client=True),
    _o("WSP Canada", ["WSP", "WSP Global"], ["engineering", "epc"], "541330", 28000,
       ["CA-QC", "CA-ON", "CA-AB", "CA-BC"], website="https://www.wsp.com/en-ca"),
    _o("AtkinsRéalis", ["SNC-Lavalin", "AtkinsRealis"], ["construction", "engineering", "epc"], "541330", 36000,
       ["CA-QC", "CA-ON", "CA-AB", "US-NY"], website="https://www.atkinsrealis.com", is_recruiter_client=True),
    _o("Hatch", ["Hatch Ltd."], ["engineering", "mining", "epc"], "541330", 9000,
       ["CA-ON", "CA-AB", "CA-BC", "CA-QC", "AU"], website="https://www.hatch.com"),
    _o("Worley Canada", ["Worley", "WorleyParsons"], ["engineering", "epc", "energy"], "541330", 5500,
       ["CA-AB", "CA-ON", "CA-BC"], website="https://www.worley.com"),
    _o("Wood Canada", ["Wood plc Canada"], ["engineering", "epc", "energy"], "541330", 4200,
       ["CA-AB", "CA-ON", "CA-NL"], website="https://www.woodplc.com"),
    _o("Fluor Canada", ["Fluor Corporation"], ["engineering", "epc"], "541330", 3500,
       ["CA-AB", "CA-ON"], website="https://www.fluor.com"),
    _o("Jacobs Canada", ["Jacobs Engineering"], ["engineering", "epc"], "541330", 4800,
       ["CA-ON", "CA-AB", "CA-QC"], website="https://www.jacobs.com"),
    _o("EXP Services", ["EXP", "EXP Global"], ["engineering"], "541330", 4000,
       ["CA-ON", "CA-AB", "CA-QC", "US-IL"], website="https://www.exp.com"),
    _o("Tetra Tech Canada", ["Tetra Tech"], ["engineering", "environmental"], "541330", 5800,
       ["CA-BC", "CA-AB", "CA-ON"], website="https://www.tetratech.com"),
    _o("McElhanney", ["McElhanney Ltd."], ["engineering", "surveying"], "541330", 1100,
       ["CA-BC", "CA-AB", "CA-YT"], website="https://www.mcelhanney.com"),

    # ---- Energy producers / midstream / pipelines ----
    _o("Suncor Energy", ["Suncor"], ["energy", "owner", "oil-gas"], "211110", 15000,
       ["CA-AB", "CA-ON"], website="https://www.suncor.com", is_recruiter_client=True),
    _o("Canadian Natural Resources", ["CNRL", "CNQ"], ["energy", "owner", "oil-gas"], "211110", 10000,
       ["CA-AB", "CA-BC", "CA-SK"], website="https://www.cnrl.com", is_recruiter_client=True),
    _o("Cenovus Energy", ["Cenovus"], ["energy", "owner", "oil-gas"], "211110", 8000,
       ["CA-AB", "CA-NL", "CA-ON"], website="https://www.cenovus.com"),
    _o("Imperial Oil", ["Imperial", "ESSO"], ["energy", "owner", "oil-gas"], "324110", 6000,
       ["CA-AB", "CA-ON"], website="https://www.imperialoil.ca"),
    _o("Tourmaline Oil", ["Tourmaline"], ["energy", "oil-gas"], "211110", 1000,
       ["CA-AB", "CA-BC"], website="https://www.tourmalineoil.com"),
    _o("ARC Resources", ["ARC"], ["energy", "oil-gas"], "211110", 950,
       ["CA-AB", "CA-BC"], website="https://www.arcresources.com"),
    _o("TC Energy", ["TransCanada", "TC Energy Corporation"], ["energy", "pipeline", "midstream"], "486210", 7800,
       ["CA-AB", "CA-ON", "US-TX"], website="https://www.tcenergy.com", is_recruiter_client=True),
    _o("Enbridge", ["Enbridge Inc."], ["energy", "pipeline", "midstream"], "486210", 12500,
       ["CA-AB", "CA-ON", "US-TX"], website="https://www.enbridge.com", is_recruiter_client=True),
    _o("Pembina Pipeline", ["Pembina"], ["energy", "pipeline", "midstream"], "486210", 4400,
       ["CA-AB", "CA-BC"], website="https://www.pembina.com"),
    _o("AltaGas", ["AltaGas Ltd."], ["energy", "midstream", "utilities"], "486210", 1800,
       ["CA-AB", "CA-BC", "US-DC"], website="https://www.altagas.ca"),
    _o("Trans Mountain Corporation", ["Trans Mountain", "TMX"], ["energy", "pipeline"], "486210", 800,
       ["CA-AB", "CA-BC"], website="https://www.transmountain.com"),

    # ---- Mining ----
    _o("Teck Resources", ["Teck"], ["mining", "owner"], "212230", 11000,
       ["CA-BC", "CA-AB", "CA-NB", "PE-CHL"], website="https://www.teck.com", is_recruiter_client=True),
    _o("Barrick Gold", ["Barrick"], ["mining", "owner"], "212220", 18000,
       ["CA-ON", "US-NV", "CL", "PE"], website="https://www.barrick.com"),
    _o("Newmont Canada", ["Newmont"], ["mining", "owner"], "212220", 5200,
       ["CA-ON", "CA-BC", "CA-NU"], website="https://www.newmont.com"),
    _o("Cameco Corporation", ["Cameco"], ["mining", "nuclear-fuel"], "212291", 3300,
       ["CA-SK", "CA-ON"], website="https://www.cameco.com"),
    _o("Lundin Mining", ["Lundin"], ["mining", "owner"], "212230", 6000,
       ["CA-ON", "CA-BC", "PT", "CL", "US-MI"], website="https://lundinmining.com"),
    _o("Agnico Eagle Mines", ["Agnico Eagle"], ["mining", "owner"], "212220", 14000,
       ["CA-QC", "CA-ON", "CA-NU"], website="https://www.agnicoeagle.com"),

    # ---- Utilities / Power ----
    _o("Hydro One", ["Hydro One Networks"], ["utilities", "power"], "221122", 9600, ["CA-ON"],
       website="https://www.hydroone.com"),
    _o("BC Hydro", ["British Columbia Hydro"], ["utilities", "power"], "221111", 6500, ["CA-BC"],
       website="https://www.bchydro.com"),
    _o("Manitoba Hydro", ["Manitoba Hydro Electric Board"], ["utilities", "power"], "221111", 5300, ["CA-MB"],
       website="https://www.hydro.mb.ca"),
    _o("SaskPower", ["Saskatchewan Power Corporation"], ["utilities", "power"], "221112", 3500, ["CA-SK"],
       website="https://www.saskpower.com"),
    _o("Ontario Power Generation", ["OPG"], ["utilities", "power", "nuclear"], "221113", 9500,
       ["CA-ON"], website="https://www.opg.com", is_recruiter_client=True),
    _o("Bruce Power", ["Bruce Power L.P."], ["utilities", "power", "nuclear"], "221113", 4200, ["CA-ON"],
       website="https://www.brucepower.com", is_recruiter_client=True),
    _o("ATCO", ["ATCO Group"], ["utilities", "power", "gas"], "221122", 6000,
       ["CA-AB", "CA-BC"], website="https://www.atco.com"),
    _o("Hydro-Québec", ["Hydro Quebec"], ["utilities", "power"], "221111", 21000, ["CA-QC"],
       website="https://www.hydroquebec.com"),
    _o("Nalcor Energy", ["Nalcor"], ["utilities", "power"], "221113", 1900, ["CA-NL"],
       website="https://nalcorenergy.com"),
]


# ---------------------------------------------------------------------------
# Postings — keyed by org canonical name. Each entry: title, region, location,
# overlay, NOC, seniority, salary range (CAD), skills, certs.
# ---------------------------------------------------------------------------

def _p(title, org, region, location, overlay, noc, seniority, low, high,
       *, skills=None, certs=None, period="annual", currency="CAD"):
    return {
        "title": title, "org": org, "region": region, "location": location,
        "overlay": overlay, "occupation_system": "NOC", "occupation_code": noc,
        "seniority": seniority, "salary_low": low, "salary_high": high,
        "currency": currency, "period": period,
        "skills": skills or [], "certifications": certs or [],
    }


POSTINGS: list[dict] = [
    # ---- PCL ----
    _p("Senior Project Manager - Infrastructure", "PCL Construction Group", "CA-AB", "Edmonton, AB",
       "construction.project-manager", "70010", "senior", 130000, 165000,
       skills=["scheduling", "procurement", "cost control", "stakeholder management"], certs=["PMP"]),
    _p("Civil Superintendent", "PCL Construction Group", "CA-AB", "Fort McMurray, AB",
       "construction.superintendent", "72014", "senior", 110000, 140000,
       skills=["concrete", "earthworks", "site logistics", "safety leadership"]),
    _p("Estimator - Heavy Civil", "PCL Construction Group", "CA-ON", "Toronto, ON",
       "construction.estimator", "22303", "intermediate", 95000, 125000,
       skills=["takeoff", "quantity surveying", "tendering"], certs=["CET"]),
    _p("Project Executive - Buildings", "PCL Construction Group", "CA-BC", "Vancouver, BC",
       "construction.project-executive", "00012", "executive", 180000, 240000,
       skills=["P&L ownership", "client management"], certs=["PMP"]),
    _p("MEP Coordinator", "PCL Construction Group", "CA-AB", "Calgary, AB",
       "construction.mep-coordinator", "22303", "intermediate", 95000, 125000,
       skills=["Revit", "BIM 360", "mechanical", "electrical"]),
    _p("Scheduler", "PCL Construction Group", "CA-MB", "Winnipeg, MB",
       "construction.scheduler", "22303", "intermediate", 90000, 115000,
       skills=["Primavera P6", "CPM"]),

    # ---- EllisDon ----
    _p("Senior Project Manager - Healthcare", "EllisDon Corporation", "CA-ON", "London, ON",
       "construction.project-manager", "70010", "senior", 135000, 170000,
       skills=["P3", "hospital construction", "infection control"], certs=["PMP"]),
    _p("Site Superintendent - Tower", "EllisDon Corporation", "CA-ON", "Toronto, ON",
       "construction.superintendent", "72014", "senior", 115000, 145000,
       skills=["high-rise", "formwork", "crane logistics"]),
    _p("BIM Manager", "EllisDon Corporation", "CA-ON", "Mississauga, ON",
       "construction.bim-manager", "22303", "intermediate", 95000, 125000,
       skills=["Revit", "Navisworks", "BIM 360"]),
    _p("Estimator - ICI", "EllisDon Corporation", "CA-NS", "Halifax, NS",
       "construction.estimator", "22303", "intermediate", 90000, 120000,
       skills=["takeoff", "subcontractor procurement"]),

    # ---- Graham ----
    _p("Construction Manager - Mining", "Graham Construction", "CA-SK", "Saskatoon, SK",
       "construction.construction-manager", "70010", "senior", 140000, 175000,
       skills=["potash", "earthworks", "subcontractor management"]),
    _p("Project Coordinator", "Graham Construction", "CA-AB", "Edmonton, AB",
       "construction.project-coordinator", "22303", "junior", 70000, 90000,
       skills=["RFIs", "submittals", "site documentation"]),
    _p("Quality Manager", "Graham Construction", "CA-BC", "Surrey, BC",
       "construction.qaqc", "22303", "senior", 105000, 135000,
       skills=["ITP", "ISO 9001"], certs=["CWB"]),

    # ---- Bird ----
    _p("Project Director - Industrial", "Bird Construction", "CA-NL", "St. John's, NL",
       "construction.project-director", "00012", "executive", 170000, 215000,
       skills=["offshore logistics", "remote camp"]),
    _p("Civil Foreman", "Bird Construction", "CA-NU", "Iqaluit, NU",
       "construction.foreman", "72014", "intermediate", 95000, 125000,
       skills=["arctic construction", "foundation"]),

    # ---- Aecon ----
    _p("Senior Cost Controller", "Aecon Group", "CA-ON", "Toronto, ON",
       "construction.cost-controller", "11100", "senior", 100000, 130000,
       skills=["EVM", "Primavera P6"]),
    _p("Project Manager - Pipeline", "Aecon Group", "CA-AB", "Edmonton, AB",
       "construction.project-manager", "70010", "senior", 140000, 180000,
       skills=["pipeline", "ROW management"], certs=["PMP"]),
    _p("Transit Construction Manager", "Aecon Group", "CA-ON", "Hamilton, ON",
       "construction.construction-manager", "70010", "senior", 145000, 185000,
       skills=["LRT", "trackwork", "tunneling"]),

    # ---- Pomerleau ----
    _p("Directeur de Projet (Project Director)", "Pomerleau", "CA-QC", "Montréal, QC",
       "construction.project-director", "00012", "executive", 170000, 210000,
       skills=["P3", "civil works"]),
    _p("Estimator - Civil", "Pomerleau", "CA-QC", "Quebec City, QC",
       "construction.estimator", "22303", "intermediate", 95000, 125000,
       skills=["takeoff", "highway"]),

    # ---- Ledcor ----
    _p("Project Manager - Renewables", "Ledcor Group", "CA-BC", "Burnaby, BC",
       "construction.project-manager", "70010", "senior", 135000, 170000,
       skills=["wind", "solar", "BESS"]),
    _p("Marine Superintendent", "Ledcor Group", "CA-BC", "Prince Rupert, BC",
       "construction.superintendent", "72014", "senior", 120000, 155000,
       skills=["marine", "piling", "wharf"]),
    _p("Telecom Outside Plant Project Manager", "Ledcor Group", "CA-AB", "Edmonton, AB",
       "construction.project-manager", "70010", "intermediate", 110000, 140000,
       skills=["fibre", "OSP", "telecom"]),

    # ---- Chandos ----
    _p("Senior Estimator - Institutional", "Chandos Construction", "CA-AB", "Edmonton, AB",
       "construction.estimator", "22303", "senior", 110000, 140000),
    _p("Carbon Manager", "Chandos Construction", "CA-ON", "Toronto, ON",
       "construction.sustainability", "21102", "intermediate", 95000, 125000,
       skills=["embodied carbon", "LEED", "Zero Carbon"], certs=["LEED AP"]),

    # ---- Modern Niagara ----
    _p("Mechanical Project Manager", "Modern Niagara", "CA-ON", "Ottawa, ON",
       "construction.mep-coordinator", "70010", "senior", 120000, 150000,
       skills=["HVAC", "plumbing", "BIM"]),
    _p("Sheet Metal Foreman", "Modern Niagara", "CA-ON", "Toronto, ON",
       "trades.sheet-metal", "72400", "journeyman", 85000, 110000,
       certs=["Red Seal"]),

    # ---- Maple Reinders ----
    _p("Wastewater Plant Construction Manager", "Maple Reinders", "CA-ON", "Mississauga, ON",
       "construction.construction-manager", "70010", "senior", 135000, 170000,
       skills=["water treatment", "plant commissioning"]),

    # ---- NACG ----
    _p("Equipment Operator - Heavy Haul", "North American Construction Group", "CA-AB", "Fort McMurray, AB",
       "trades.heavy-equipment-operator", "73400", "journeyman", 85000, 115000),
    _p("Mine Operations Manager", "North American Construction Group", "CA-AB", "Fort McMurray, AB",
       "mining.operations-manager", "70010", "senior", 165000, 210000,
       skills=["oil sands", "haul truck fleet"]),

    # ---- Aldridge Pipeline ----
    _p("Pipeline Construction Manager", "Aldridge Pipeline", "CA-AB", "Grande Prairie, AB",
       "construction.construction-manager", "70010", "senior", 145000, 185000,
       skills=["mainline pipeline", "right-of-way"]),
    _p("Pipeline Inspector", "Aldridge Pipeline", "CA-SK", "Regina, SK",
       "construction.qaqc", "22303", "intermediate", 95000, 125000,
       certs=["NACE"]),

    # ---- Stantec ----
    _p("Senior Mechanical Engineer", "Stantec", "CA-AB", "Edmonton, AB",
       "engineering.mechanical", "21301", "senior", 115000, 150000,
       skills=["HVAC", "industrial", "process"], certs=["PEng"]),
    _p("Project Manager - Water/Wastewater", "Stantec", "CA-BC", "Vancouver, BC",
       "engineering.project-manager", "70010", "senior", 130000, 165000,
       skills=["water treatment", "municipal"], certs=["PEng", "PMP"]),
    _p("Geotechnical Engineer", "Stantec", "CA-ON", "Toronto, ON",
       "engineering.geotechnical", "21331", "intermediate", 90000, 120000,
       certs=["PEng"]),
    _p("Bridge Designer", "Stantec", "CA-QC", "Montréal, QC",
       "engineering.structural", "21300", "intermediate", 95000, 125000,
       skills=["concrete bridges", "steel bridges", "AASHTO"], certs=["ing."]),

    # ---- WSP ----
    _p("Transportation Project Manager", "WSP Canada", "CA-ON", "Thornhill, ON",
       "engineering.project-manager", "70010", "senior", 130000, 165000,
       skills=["highway", "MTO", "transit"], certs=["PEng"]),
    _p("Senior Electrical Engineer", "WSP Canada", "CA-AB", "Calgary, AB",
       "engineering.electrical", "21310", "senior", 115000, 150000,
       skills=["substations", "transmission", "protection"], certs=["PEng"]),
    _p("Environmental Lead", "WSP Canada", "CA-BC", "Victoria, BC",
       "engineering.environmental", "21102", "senior", 110000, 140000,
       skills=["EA", "EIS", "permitting"]),

    # ---- AtkinsRéalis ----
    _p("Project Director - Transit", "AtkinsRéalis", "CA-QC", "Montréal, QC",
       "construction.project-director", "00012", "executive", 175000, 215000,
       skills=["P3", "transit", "MEP coordination"], certs=["PEng", "PMP"]),
    _p("Senior Civil Engineer", "AtkinsRéalis", "CA-ON", "Toronto, ON",
       "engineering.civil", "21300", "senior", 115000, 150000,
       skills=["rail", "highway"], certs=["PEng"]),
    _p("Nuclear Mechanical Engineer", "AtkinsRéalis", "CA-ON", "Mississauga, ON",
       "engineering.nuclear", "21301", "senior", 130000, 170000,
       skills=["CANDU", "reactor systems"], certs=["PEng"]),

    # ---- Hatch ----
    _p("Process Engineer - Metallurgy", "Hatch", "CA-ON", "Mississauga, ON",
       "engineering.process", "21301", "intermediate", 100000, 135000,
       skills=["mineral processing", "smelting"], certs=["PEng"]),
    _p("Tailings Engineer", "Hatch", "CA-BC", "Vancouver, BC",
       "engineering.geotechnical", "21331", "senior", 130000, 170000,
       skills=["tailings dam", "geotechnical"], certs=["PEng"]),
    _p("Project Manager - Aluminum Smelter", "Hatch", "CA-QC", "Saguenay, QC",
       "engineering.project-manager", "70010", "senior", 145000, 185000,
       skills=["smelter", "primary metals"], certs=["PEng", "PMP"]),

    # ---- Worley ----
    _p("Senior Pipeline Engineer", "Worley Canada", "CA-AB", "Calgary, AB",
       "engineering.pipeline", "21301", "senior", 130000, 175000,
       skills=["B31.8", "B31.4", "pipeline design"], certs=["PEng"]),
    _p("Commissioning Engineer - LNG", "Worley Canada", "CA-BC", "Kitimat, BC",
       "energy.commissioning-engineer", "21301", "senior", 140000, 185000,
       skills=["LNG", "systems completions"], certs=["PEng"]),

    # ---- Wood Canada ----
    _p("Senior Process Engineer - Oil Sands", "Wood Canada", "CA-AB", "Calgary, AB",
       "engineering.process", "21301", "senior", 130000, 170000,
       skills=["SAGD", "oil sands", "HYSYS"], certs=["PEng"]),
    _p("Mechanical Designer", "Wood Canada", "CA-NL", "St. John's, NL",
       "engineering.mechanical", "22301", "intermediate", 85000, 115000,
       skills=["offshore", "AutoCAD Plant 3D"]),

    # ---- Fluor Canada ----
    _p("EPCM Project Manager", "Fluor Canada", "CA-AB", "Calgary, AB",
       "engineering.project-manager", "70010", "senior", 155000, 200000,
       certs=["PMP", "PEng"]),
    _p("Senior Cost Engineer", "Fluor Canada", "CA-AB", "Calgary, AB",
       "construction.cost-controller", "11100", "senior", 110000, 140000,
       skills=["EVM", "EcoSys"]),

    # ---- Jacobs Canada ----
    _p("Senior Project Engineer - Defense", "Jacobs Canada", "CA-ON", "Ottawa, ON",
       "engineering.project-manager", "21301", "senior", 125000, 165000,
       skills=["defense", "ITAR"], certs=["PEng"]),

    # ---- Suncor ----
    _p("Completions Engineer", "Suncor Energy", "CA-AB", "Fort McMurray, AB",
       "energy.completions-engineer", "21331", "intermediate", 130000, 175000,
       skills=["well intervention", "pressure testing"], certs=["PEng"]),
    _p("Reservoir Engineer", "Suncor Energy", "CA-AB", "Calgary, AB",
       "energy.reservoir-engineer", "21331", "senior", 145000, 185000,
       skills=["reservoir simulation", "decline curve analysis", "Petrel"], certs=["PEng"]),
    _p("Maintenance Superintendent", "Suncor Energy", "CA-AB", "Fort McMurray, AB",
       "industrial.maintenance-superintendent", "72014", "senior", 120000, 150000,
       skills=["turnaround planning", "reliability", "SAP PM"]),
    _p("Shutdown Coordinator", "Suncor Energy", "CA-AB", "Fort McMurray, AB",
       "industrial.shutdown-coordinator", "72014", "senior", 130000, 160000,
       skills=["TA planning", "scheduling"]),
    _p("Pipefitter (Red Seal)", "Suncor Energy", "CA-AB", "Fort McMurray, AB",
       "trades.pipefitter", "72301", "journeyman", 84000, 110000,
       skills=["pipe fabrication"], certs=["Red Seal"]),
    _p("Senior Process Engineer", "Suncor Energy", "CA-AB", "Edmonton, AB",
       "engineering.process", "21301", "senior", 135000, 175000,
       skills=["refining", "HYSYS", "PHA"], certs=["PEng"]),

    # ---- CNRL ----
    _p("Drilling Engineer", "Canadian Natural Resources", "CA-AB", "Calgary, AB",
       "energy.drilling-engineer", "21331", "intermediate", 130000, 170000,
       skills=["horizontal drilling", "well design"], certs=["PEng"]),
    _p("Production Foreman", "Canadian Natural Resources", "CA-AB", "Fort McMurray, AB",
       "industrial.production-foreman", "72100", "journeyman", 110000, 140000),
    _p("Reliability Engineer", "Canadian Natural Resources", "CA-AB", "Bonnyville, AB",
       "industrial.reliability-engineer", "21301", "senior", 125000, 165000,
       skills=["RCM", "vibration analysis"], certs=["PEng"]),

    # ---- Cenovus ----
    _p("Well Site Manager", "Cenovus Energy", "CA-AB", "Conklin, AB",
       "energy.well-site-manager", "72100", "senior", 130000, 165000),
    _p("Process Safety Engineer", "Cenovus Energy", "CA-NL", "St. John's, NL",
       "engineering.process-safety", "21301", "senior", 130000, 170000,
       skills=["PHA", "HAZOP", "PSM"], certs=["PEng"]),

    # ---- Imperial Oil ----
    _p("Refinery Operations Engineer", "Imperial Oil", "CA-AB", "Edmonton, AB",
       "engineering.process", "21301", "intermediate", 110000, 140000,
       certs=["PEng"]),
    _p("Mechanical Reliability Engineer", "Imperial Oil", "CA-ON", "Sarnia, ON",
       "industrial.reliability-engineer", "21301", "intermediate", 110000, 145000,
       certs=["PEng"]),

    # ---- Tourmaline ----
    _p("Senior Facilities Engineer", "Tourmaline Oil", "CA-AB", "Calgary, AB",
       "energy.facilities-engineer", "21301", "senior", 135000, 175000,
       certs=["PEng"]),

    # ---- ARC Resources ----
    _p("Production Engineer", "ARC Resources", "CA-AB", "Grande Prairie, AB",
       "energy.production-engineer", "21331", "intermediate", 110000, 145000,
       certs=["PEng"]),

    # ---- TC Energy ----
    _p("Senior Pipeline Engineer", "TC Energy", "CA-AB", "Calgary, AB",
       "engineering.pipeline", "21301", "senior", 140000, 180000,
       skills=["natural gas pipeline", "B31.8"], certs=["PEng"]),
    _p("Construction Manager - Mainline", "TC Energy", "CA-BC", "Prince George, BC",
       "construction.construction-manager", "70010", "senior", 150000, 190000),
    _p("ROW Land Agent", "TC Energy", "CA-AB", "Edmonton, AB",
       "energy.land-agent", "12013", "intermediate", 85000, 115000),

    # ---- Enbridge ----
    _p("Senior Integrity Engineer", "Enbridge", "CA-AB", "Edmonton, AB",
       "engineering.pipeline-integrity", "21301", "senior", 135000, 175000,
       skills=["ILI", "B31.8S"], certs=["PEng"]),
    _p("Pipeline Operations Supervisor", "Enbridge", "CA-ON", "Sarnia, ON",
       "industrial.operations-supervisor", "72100", "senior", 115000, 145000),
    _p("Senior Cyber Security Analyst - OT", "Enbridge", "CA-AB", "Calgary, AB",
       "engineering.ot-security", "21222", "senior", 130000, 165000,
       skills=["SCADA", "OT/IT", "NERC CIP"]),

    # ---- Pembina ----
    _p("Project Engineer - Midstream", "Pembina Pipeline", "CA-AB", "Calgary, AB",
       "engineering.project-manager", "21301", "intermediate", 115000, 150000,
       certs=["PEng"]),
    _p("Plant Manager - Fractionation", "Pembina Pipeline", "CA-AB", "Redwater, AB",
       "industrial.plant-manager", "70010", "senior", 165000, 210000),

    # ---- AltaGas ----
    _p("Senior Gas Engineer", "AltaGas", "CA-AB", "Calgary, AB",
       "energy.facilities-engineer", "21301", "senior", 130000, 170000,
       certs=["PEng"]),

    # ---- Trans Mountain ----
    _p("Commissioning Manager", "Trans Mountain Corporation", "CA-AB", "Edmonton, AB",
       "energy.commissioning-manager", "70010", "senior", 155000, 200000),
    _p("Senior Project Controls Manager", "Trans Mountain Corporation", "CA-BC", "Burnaby, BC",
       "construction.cost-controller", "11100", "senior", 130000, 170000),

    # ---- Teck ----
    _p("Mine Engineer", "Teck Resources", "CA-BC", "Sparwood, BC",
       "mining.mine-engineer", "21330", "intermediate", 110000, 145000,
       certs=["PEng"]),
    _p("Mill Superintendent", "Teck Resources", "CA-BC", "Trail, BC",
       "mining.mill-superintendent", "72014", "senior", 140000, 180000),
    _p("Concentrator Process Engineer", "Teck Resources", "CA-BC", "Logan Lake, BC",
       "engineering.process", "21301", "intermediate", 105000, 140000,
       skills=["flotation", "comminution"], certs=["PEng"]),

    # ---- Barrick ----
    _p("Senior Geologist", "Barrick Gold", "CA-ON", "Toronto, ON",
       "mining.geologist", "21102", "senior", 130000, 170000),

    # ---- Newmont Canada ----
    _p("Underground Mine Captain", "Newmont Canada", "CA-ON", "Timmins, ON",
       "mining.mine-captain", "72022", "journeyman", 130000, 165000),

    # ---- Cameco ----
    _p("Radiation Safety Officer", "Cameco Corporation", "CA-SK", "Saskatoon, SK",
       "industrial.radiation-safety", "21102", "senior", 115000, 150000,
       certs=["CHP"]),
    _p("Senior Mining Engineer", "Cameco Corporation", "CA-SK", "Cigar Lake, SK",
       "mining.mine-engineer", "21330", "senior", 135000, 175000,
       certs=["PEng"]),

    # ---- Lundin ----
    _p("Tailings Engineer - Eagle Mine", "Lundin Mining", "CA-ON", "Toronto, ON",
       "engineering.geotechnical", "21331", "senior", 125000, 165000,
       certs=["PEng"]),

    # ---- Agnico Eagle ----
    _p("Mine Manager", "Agnico Eagle Mines", "CA-NU", "Rankin Inlet, NU",
       "mining.mine-manager", "70010", "senior", 180000, 230000),
    _p("Mill Operator", "Agnico Eagle Mines", "CA-QC", "Val-d'Or, QC",
       "trades.mill-operator", "94130", "journeyman", 95000, 125000),

    # ---- Hydro One ----
    _p("Substation Project Manager", "Hydro One", "CA-ON", "Toronto, ON",
       "engineering.project-manager", "70010", "senior", 125000, 160000,
       skills=["transmission", "substation"], certs=["PEng"]),
    _p("Powerline Technician (Red Seal)", "Hydro One", "CA-ON", "London, ON",
       "trades.powerline-technician", "72202", "journeyman", 105000, 135000,
       certs=["Red Seal"]),

    # ---- BC Hydro ----
    _p("Senior Civil Engineer - Dams", "BC Hydro", "CA-BC", "Vancouver, BC",
       "engineering.civil", "21300", "senior", 135000, 175000,
       skills=["dam safety", "hydraulics"], certs=["PEng"]),
    _p("Generation Maintenance Manager - Site C", "BC Hydro", "CA-BC", "Fort St. John, BC",
       "industrial.maintenance-manager", "70010", "senior", 145000, 185000),

    # ---- Manitoba Hydro ----
    _p("Power System Operator", "Manitoba Hydro", "CA-MB", "Winnipeg, MB",
       "industrial.system-operator", "72202", "journeyman", 110000, 140000),

    # ---- SaskPower ----
    _p("Carbon Capture Engineer", "SaskPower", "CA-SK", "Estevan, SK",
       "engineering.process", "21301", "senior", 130000, 170000,
       skills=["CCS", "amine systems"], certs=["PEng"]),

    # ---- OPG / Bruce Power ----
    _p("Reactor Operator", "Ontario Power Generation", "CA-ON", "Pickering, ON",
       "industrial.reactor-operator", "92100", "senior", 145000, 180000,
       certs=["CNSC operator"]),
    _p("Senior Nuclear Safety Engineer", "Ontario Power Generation", "CA-ON", "Clarington, ON",
       "engineering.nuclear", "21301", "senior", 140000, 180000,
       certs=["PEng"]),
    _p("Project Manager - SMR", "Ontario Power Generation", "CA-ON", "Clarington, ON",
       "engineering.project-manager", "70010", "senior", 145000, 185000,
       skills=["SMR", "BWRX-300"], certs=["PEng", "PMP"]),
    _p("Refurbishment Construction Manager", "Bruce Power", "CA-ON", "Kincardine, ON",
       "construction.construction-manager", "70010", "senior", 155000, 195000),
    _p("Nuclear Quality Engineer", "Bruce Power", "CA-ON", "Tiverton, ON",
       "engineering.qaqc", "21301", "intermediate", 110000, 145000,
       certs=["PEng"]),

    # ---- ATCO ----
    _p("Gas Distribution Foreman", "ATCO", "CA-AB", "Calgary, AB",
       "trades.gas-distribution", "72500", "journeyman", 105000, 135000,
       certs=["Red Seal"]),

    # ---- Hydro-Québec ----
    _p("Ingénieur Senior - Transport", "Hydro-Québec", "CA-QC", "Montréal, QC",
       "engineering.electrical", "21310", "senior", 120000, 160000,
       skills=["transmission", "735 kV"], certs=["ing."]),
    _p("Chargé de Projet - Barrage", "Hydro-Québec", "CA-QC", "Baie-Comeau, QC",
       "engineering.project-manager", "70010", "senior", 130000, 170000,
       skills=["hydroelectric"]),

    # ---- Nalcor ----
    _p("Senior Generation Engineer", "Nalcor Energy", "CA-NL", "St. John's, NL",
       "engineering.electrical", "21310", "senior", 115000, 150000,
       certs=["PEng"]),
]


# ---------------------------------------------------------------------------
# Named projects — Canadian construction / infrastructure / energy pipeline.
# ---------------------------------------------------------------------------

PROJECTS: list[dict] = [
    {"name": "Trans Mountain Pipeline Expansion - Edmonton Terminal", "project_type": "pipeline",
     "region": "CA-AB", "location": "Edmonton, AB", "capex_usd": 21_400_000_000,
     "peak_headcount": 7600, "construction_start": date(2019, 12, 3),
     "expected_completion": date(2026, 5, 1), "source": "Trans Mountain Corporation"},
    {"name": "LNG Canada Phase 2", "project_type": "lng", "region": "CA-BC",
     "location": "Kitimat, BC", "capex_usd": 14_000_000_000, "peak_headcount": 4500,
     "announced_on": date(2024, 11, 1), "construction_start": date(2026, 9, 1),
     "expected_completion": date(2030, 6, 1), "source": "Shell / LNG Canada JV"},
    {"name": "Coastal GasLink Pipeline - Section 7", "project_type": "pipeline",
     "region": "CA-BC", "location": "Kitimat, BC", "capex_usd": 14_500_000_000,
     "peak_headcount": 6000, "construction_start": date(2019, 4, 1),
     "expected_completion": date(2025, 12, 1), "source": "TC Energy"},
    {"name": "Site C Hydroelectric Dam", "project_type": "hydroelectric", "region": "CA-BC",
     "location": "Fort St. John, BC", "capex_usd": 16_000_000_000, "peak_headcount": 4500,
     "construction_start": date(2015, 7, 1), "expected_completion": date(2025, 12, 1),
     "source": "BC Hydro"},
    {"name": "Darlington Nuclear Refurbishment", "project_type": "nuclear", "region": "CA-ON",
     "location": "Clarington, ON", "capex_usd": 12_800_000_000, "peak_headcount": 4500,
     "construction_start": date(2016, 10, 1), "expected_completion": date(2026, 12, 1),
     "source": "Ontario Power Generation"},
    {"name": "Bruce Power MCR Unit 6 Refurbishment", "project_type": "nuclear", "region": "CA-ON",
     "location": "Tiverton, ON", "capex_usd": 6_200_000_000, "peak_headcount": 4000,
     "construction_start": date(2020, 1, 1), "expected_completion": date(2026, 6, 1),
     "source": "Bruce Power"},
    {"name": "BWRX-300 Small Modular Reactor - Darlington", "project_type": "nuclear",
     "region": "CA-ON", "location": "Clarington, ON", "capex_usd": 5_000_000_000,
     "peak_headcount": 1700, "announced_on": date(2022, 12, 2),
     "construction_start": date(2025, 6, 1), "expected_completion": date(2029, 12, 1),
     "source": "Ontario Power Generation / GE Hitachi"},
    {"name": "Ontario Line - South Civil, Stations & Tunnel", "project_type": "transit",
     "region": "CA-ON", "location": "Toronto, ON", "capex_usd": 3_900_000_000,
     "peak_headcount": 2400, "construction_start": date(2022, 9, 1),
     "expected_completion": date(2031, 12, 1), "source": "Metrolinx"},
    {"name": "REM (Réseau express métropolitain)", "project_type": "transit", "region": "CA-QC",
     "location": "Montréal, QC", "capex_usd": 6_900_000_000, "peak_headcount": 3000,
     "construction_start": date(2018, 4, 1), "expected_completion": date(2027, 12, 1),
     "source": "CDPQ Infra"},
    {"name": "Eglinton Crosstown West Extension", "project_type": "transit", "region": "CA-ON",
     "location": "Toronto, ON", "capex_usd": 4_700_000_000, "peak_headcount": 2200,
     "construction_start": date(2020, 9, 1), "expected_completion": date(2030, 12, 1),
     "source": "Metrolinx"},
    {"name": "Hamilton LRT", "project_type": "transit", "region": "CA-ON",
     "location": "Hamilton, ON", "capex_usd": 3_400_000_000, "peak_headcount": 1800,
     "construction_start": date(2024, 6, 1), "expected_completion": date(2030, 12, 1),
     "source": "Metrolinx"},
    {"name": "Green Line LRT - Stage 1", "project_type": "transit", "region": "CA-AB",
     "location": "Calgary, AB", "capex_usd": 5_500_000_000, "peak_headcount": 1500,
     "construction_start": date(2024, 1, 1), "expected_completion": date(2030, 6, 1),
     "source": "City of Calgary"},
    {"name": "Edmonton Valley Line West LRT", "project_type": "transit", "region": "CA-AB",
     "location": "Edmonton, AB", "capex_usd": 1_900_000_000, "peak_headcount": 1100,
     "construction_start": date(2021, 6, 1), "expected_completion": date(2028, 12, 1),
     "source": "City of Edmonton"},
    {"name": "GTA West Highway (Highway 413)", "project_type": "highway", "region": "CA-ON",
     "location": "Caledon, ON", "capex_usd": 6_000_000_000, "peak_headcount": 1800,
     "construction_start": date(2026, 6, 1), "expected_completion": date(2032, 12, 1),
     "source": "Government of Ontario"},
    {"name": "Ring of Fire - Marten Falls Access Road", "project_type": "mining-infrastructure",
     "region": "CA-ON", "location": "James Bay Lowlands, ON", "capex_usd": 1_200_000_000,
     "peak_headcount": 800, "announced_on": date(2021, 3, 2),
     "expected_completion": date(2030, 12, 1), "source": "Government of Ontario"},
    {"name": "Cigar Lake Mine Expansion", "project_type": "mining", "region": "CA-SK",
     "location": "Cigar Lake, SK", "capex_usd": 600_000_000, "peak_headcount": 700,
     "construction_start": date(2024, 1, 1), "expected_completion": date(2027, 12, 1),
     "source": "Cameco Corporation"},
    {"name": "Voisey's Bay Underground Mine Expansion", "project_type": "mining",
     "region": "CA-NL", "location": "Voisey's Bay, NL", "capex_usd": 2_400_000_000,
     "peak_headcount": 1600, "construction_start": date(2020, 6, 1),
     "expected_completion": date(2026, 6, 1), "source": "Vale Canada"},
    {"name": "Detour Lake Underground Expansion", "project_type": "mining", "region": "CA-ON",
     "location": "Cochrane, ON", "capex_usd": 1_100_000_000, "peak_headcount": 900,
     "construction_start": date(2024, 1, 1), "expected_completion": date(2028, 6, 1),
     "source": "Agnico Eagle Mines"},
    {"name": "Edmonton Hydrogen Hub - Air Products Net-Zero Plant", "project_type": "hydrogen",
     "region": "CA-AB", "location": "Sturgeon County, AB", "capex_usd": 1_600_000_000,
     "peak_headcount": 1100, "construction_start": date(2022, 6, 1),
     "expected_completion": date(2026, 6, 1), "source": "Air Products"},
    {"name": "Iqaluit International Airport Modernization", "project_type": "infrastructure",
     "region": "CA-NU", "location": "Iqaluit, NU", "capex_usd": 300_000_000, "peak_headcount": 450,
     "construction_start": date(2025, 6, 1), "expected_completion": date(2028, 12, 1),
     "source": "Government of Nunavut"},
    {"name": "NewBridge Halifax - Macdonald Bridge Replacement Study", "project_type": "infrastructure",
     "region": "CA-NS", "location": "Halifax, NS", "capex_usd": 2_000_000_000, "peak_headcount": 600,
     "announced_on": date(2024, 9, 1), "source": "Halifax Harbour Bridges"},
    {"name": "Pickering 'B' Refurbishment (Feasibility)", "project_type": "nuclear",
     "region": "CA-ON", "location": "Pickering, ON", "capex_usd": 2_000_000_000,
     "peak_headcount": 2500, "announced_on": date(2024, 1, 9),
     "source": "Ontario Power Generation"},
    {"name": "Hertz Solar Generation Project", "project_type": "renewable", "region": "CA-AB",
     "location": "Vulcan County, AB", "capex_usd": 540_000_000, "peak_headcount": 400,
     "construction_start": date(2024, 9, 1), "expected_completion": date(2026, 6, 1),
     "source": "TransAlta"},
    {"name": "Maritime Link HVDC Subsea Cable", "project_type": "transmission", "region": "CA-NS",
     "location": "Cape Breton, NS", "capex_usd": 1_700_000_000, "peak_headcount": 800,
     "construction_start": date(2014, 7, 1), "expected_completion": date(2017, 12, 1),
     "source": "Emera"},
    {"name": "Manitoba Hydro Bipole III", "project_type": "transmission", "region": "CA-MB",
     "location": "Manitoba", "capex_usd": 4_700_000_000, "peak_headcount": 1500,
     "construction_start": date(2013, 6, 1), "expected_completion": date(2018, 7, 1),
     "source": "Manitoba Hydro"},
]


# ---------------------------------------------------------------------------
# Apply: idempotent insert/upsert. Returns counts.
# ---------------------------------------------------------------------------

def apply(db: Session) -> SeedDemoResult:
    org_by_name: dict[str, Organization] = {}
    orgs_added = 0
    for spec in ORGS:
        existing = db.execute(
            select(Organization).where(Organization.canonical_name == spec["canonical_name"])
        ).scalar_one_or_none()
        if existing is None:
            existing = Organization(**spec)
            db.add(existing)
            db.flush()
            orgs_added += 1
        org_by_name[spec["canonical_name"]] = existing

    postings_added = 0
    for spec in POSTINGS:
        org = org_by_name.get(spec["org"])
        if org is None:
            continue
        dedup_key = hashlib.sha256(
            f"demo:{spec['org']}:{spec['title']}:{spec['region']}".encode()
        ).hexdigest()
        existing = db.execute(
            select(Posting).where(Posting.dedup_key == dedup_key)
        ).scalar_one_or_none()
        if existing is not None:
            existing.last_seen_at = NOW
            existing.source_count = (existing.source_count or 1) + 1
            continue

        posting = Posting(
            organization_id=org.id,
            title=spec["title"],
            occupation_code=spec.get("occupation_code"),
            occupation_system=spec.get("occupation_system"),
            industrial_overlay_code=spec.get("overlay"),
            seniority=spec.get("seniority"),
            region_code=spec["region"],
            location_text=spec.get("location"),
            salary_low=Decimal(str(spec["salary_low"])) if spec.get("salary_low") else None,
            salary_high=Decimal(str(spec["salary_high"])) if spec.get("salary_high") else None,
            salary_currency=spec.get("currency"),
            salary_period=spec.get("period"),
            skills=spec.get("skills", []),
            certifications=spec.get("certifications", []),
            first_seen_at=NOW - timedelta(days=14),
            last_seen_at=NOW,
            is_active=True,
            source_count=1,
            dedup_key=dedup_key,
            confidence={"occupation": 0.95, "source": "seed-demo"},
        )
        db.add(posting)
        db.flush()

        raw_id = f"seed-{dedup_key[:16]}"
        existing_raw = db.execute(
            select(RawPosting).where(
                RawPosting.source == "seed-demo",
                RawPosting.source_posting_id == raw_id,
            )
        ).scalar_one_or_none()
        if existing_raw is None:
            db.add(
                RawPosting(
                    source="seed-demo",
                    source_posting_id=raw_id,
                    source_url=f"seed://{raw_id}",
                    raw_title=spec["title"],
                    company_raw=spec["org"],
                    location_raw=spec.get("location"),
                    posted_date=TODAY - timedelta(days=14),
                    html_hash=dedup_key,
                    scraped_at=NOW,
                    posting_id=posting.id,
                    extra={"seed": True},
                )
            )
        postings_added += 1

    # Compensation: pull one record per unique (overlay, region, seniority) at
    # the midpoint of its posting band, with placement_verified provenance.
    comp_added = 0
    seen_keys: set[tuple] = set()
    for i, spec in enumerate(POSTINGS):
        key = (spec.get("overlay"), spec["region"], spec.get("seniority"))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        org = org_by_name.get(spec["org"])
        observed_on = TODAY - timedelta(days=30 + i * 2)
        mid = (spec["salary_low"] + spec["salary_high"]) / 2
        existing_comp = db.execute(
            select(CompensationRecord).where(
                CompensationRecord.industrial_overlay_code == spec["overlay"],
                CompensationRecord.region_code == spec["region"],
                CompensationRecord.seniority == spec.get("seniority"),
                CompensationRecord.observed_on == observed_on,
            )
        ).scalar_one_or_none()
        if existing_comp is not None:
            continue
        db.add(
            CompensationRecord(
                industrial_overlay_code=spec["overlay"],
                occupation_code=spec.get("occupation_code"),
                occupation_system=spec.get("occupation_system"),
                seniority=spec.get("seniority"),
                region_code=spec["region"],
                sector=(org.sector_tags[0] if org and org.sector_tags else None),
                amount_low=Decimal(str(spec["salary_low"])),
                amount_mid=Decimal(str(mid)),
                amount_high=Decimal(str(spec["salary_high"])),
                currency=spec["currency"],
                period=spec["period"],
                source_type="placement_verified",
                confidence=Decimal("0.95"),
                observed_on=observed_on,
            )
        )
        comp_added += 1

    projects_added = 0
    for spec in PROJECTS:
        existing = db.execute(
            select(Project).where(Project.name == spec["name"])
        ).scalar_one_or_none()
        if existing is not None:
            continue
        db.add(
            Project(
                name=spec["name"],
                project_type=spec["project_type"],
                region_code=spec["region"],
                location_text=spec.get("location"),
                capex_usd=Decimal(str(spec["capex_usd"])) if spec.get("capex_usd") else None,
                estimated_peak_headcount=spec.get("peak_headcount"),
                announced_on=spec.get("announced_on"),
                construction_start_on=spec.get("construction_start"),
                expected_completion_on=spec.get("expected_completion"),
                source=spec.get("source"),
            )
        )
        projects_added += 1

    db.commit()

    canonical_total = int(db.scalar(select(func.count()).select_from(Posting)) or 0)
    raw_total = int(db.scalar(select(func.count()).select_from(RawPosting)) or 0)

    return SeedDemoResult(
        organizations_added=orgs_added,
        postings_added=postings_added,
        compensation_added=comp_added,
        projects_added=projects_added,
        canonical_postings_total=canonical_total,
        raw_postings_total=raw_total,
    )
