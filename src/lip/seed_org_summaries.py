"""Factual one-paragraph summaries for each org in the Canadian seed.

Kept in a separate module so seed_demo stays focused on structure.
Sourced from public company profiles (corporate About pages, annual
reports). Refreshed manually when material changes; not a moat asset,
just useful UI context.
"""

SUMMARIES: dict[str, str] = {
    # ---- General Contractors ----
    "PCL Construction Group": (
        "Employee-owned construction company based in Edmonton, ranked one of "
        "the largest GCs in North America. Active across buildings, civil, "
        "industrial, and heavy-industrial work, with major presence in "
        "Alberta oil sands, Ontario healthcare, and US west-coast markets."
    ),
    "EllisDon Corporation": (
        "Canadian construction services company headquartered in Mississauga, "
        "executing roughly $5B in annual revenue across buildings, civil "
        "infrastructure, and P3 healthcare delivery. Known for hospital and "
        "transit project delivery across Ontario and Atlantic Canada."
    ),
    "Graham Construction": (
        "Calgary-headquartered, employee-owned construction firm specializing "
        "in buildings, industrial, and infrastructure projects across Western "
        "Canada and the US Pacific Northwest. Strong potash, water-treatment, "
        "and healthcare delivery."
    ),
    "Bird Construction": (
        "Mississauga-based construction services firm focused on industrial, "
        "buildings, and infrastructure work. Active in Atlantic Canada, "
        "Northern Canada (including Nunavut), and Alberta oil sands."
    ),
    "Aecon Group": (
        "Toronto-based construction and infrastructure development company "
        "with operations across nuclear, transit, utilities, and civil "
        "sectors. Holds significant exposure to Darlington refurbishment "
        "and Toronto-area transit megaprojects."
    ),
    "Pomerleau": (
        "Quebec-headquartered general contractor and one of the largest "
        "construction firms in Canada. Delivers buildings and civil works "
        "primarily across Quebec, Ontario, and Western Canada, with active "
        "P3 programs."
    ),
    "Ledcor Group": (
        "Privately-held diversified construction, infrastructure, and "
        "telecommunications company based in Vancouver. Operates across "
        "civil, oil & gas, mining, telecom, and marine sectors in Western "
        "Canada and the Pacific Northwest US."
    ),
    "Chandos Construction": (
        "Employee-owned, B-Corp certified construction company headquartered "
        "in Edmonton with offices across Western Canada and Ontario. Focused "
        "on institutional, commercial, and zero-carbon building delivery."
    ),
    "Modern Niagara": (
        "Mechanical, electrical, and integrated building-systems contractor "
        "with offices across Canada. One of the country's largest MEP firms, "
        "with a strong sustainability and net-zero retrofit practice."
    ),
    "Maple Reinders": (
        "Ontario-based general contractor specializing in environmental "
        "(water/wastewater treatment), institutional, and design-build "
        "projects across Canada."
    ),
    "Walsh Canada": (
        "Canadian operations of Walsh Group, a Chicago-headquartered general "
        "contractor. Active on transit and infrastructure in Toronto."
    ),
    "North American Construction Group": (
        "Heavy civil and mining services contractor headquartered in Acheson, "
        "Alberta. Provides earthworks, mining contracting, and equipment "
        "services to oil sands and mining clients across North America."
    ),
    "Aldridge Pipeline": (
        "Pipeline construction contractor with Canadian operations in Alberta, "
        "British Columbia, and Saskatchewan, executing oil and gas mainline "
        "and integrity work."
    ),
    "Tarsus Building Group": (
        "Ontario-based construction company focused on commercial and "
        "institutional building delivery."
    ),
    "Bondfield Construction": (
        "Ontario-based general contractor historically active in institutional "
        "and healthcare delivery."
    ),

    # ---- Engineering / EPC ----
    "Stantec": (
        "Edmonton-headquartered global engineering and design services firm "
        "with ~32,000 employees across 400+ offices. Practices span "
        "buildings, water, transportation, mining, energy, and environmental "
        "services."
    ),
    "WSP Canada": (
        "Canadian arm of WSP Global, a Montreal-headquartered professional "
        "services firm. Active in transportation, buildings, environment, "
        "and earth and energy across all Canadian provinces."
    ),
    "AtkinsRéalis": (
        "Formerly SNC-Lavalin. Montreal-based global engineering and project "
        "management firm. Major practices in nuclear (CANDU), transit, mining "
        "& metallurgy, infrastructure, and clean power."
    ),
    "Hatch": (
        "Mississauga-based global engineering, project management, and "
        "professional services firm specializing in metals and minerals, "
        "energy, and infrastructure. Employee-owned, ~9,000 staff."
    ),
    "Worley Canada": (
        "Canadian operations of Worley, an Australian-headquartered global "
        "professional services company in energy, chemicals, and resources. "
        "Strong Alberta oil sands and pipeline engineering practice."
    ),
    "Wood Canada": (
        "Canadian arm of Wood plc, a UK-based engineering and consulting firm "
        "serving energy, materials, and infrastructure markets. Active in "
        "Alberta oil and gas and Atlantic Canada offshore."
    ),
    "Fluor Canada": (
        "Canadian division of Fluor Corporation, a major global EPC firm. "
        "Calgary office leads oil sands and downstream energy execution."
    ),
    "Jacobs Canada": (
        "Canadian operations of Jacobs, a US-based professional services "
        "firm covering aerospace, defense, energy, and infrastructure."
    ),
    "EXP Services": (
        "Brampton-headquartered engineering, architecture, design, and "
        "consulting firm with ~4,000 employees across Canada and the US."
    ),
    "Tetra Tech Canada": (
        "Canadian arm of Tetra Tech, a US-based provider of consulting and "
        "engineering services in water, environment, and energy."
    ),
    "McElhanney": (
        "Employee-owned engineering, surveying, and mapping firm with offices "
        "across British Columbia, Alberta, and Yukon. Focused on transportation, "
        "land development, and resource access."
    ),

    # ---- Energy ----
    "Suncor Energy": (
        "Calgary-based integrated energy company. Operates oil sands mining "
        "and in-situ assets in Alberta, four refineries, and the Petro-Canada "
        "retail network. Largest in-situ producer in Canada by output."
    ),
    "Canadian Natural Resources": (
        "Calgary-based independent crude oil and natural gas producer with the "
        "largest production base in Canada. Major assets across oil sands, "
        "heavy oil, and conventional plays."
    ),
    "Cenovus Energy": (
        "Calgary-based integrated oil and gas company, formed from the 2020 "
        "Husky merger. Operates oil sands in-situ (Christina Lake, Foster "
        "Creek), offshore Atlantic Canada, and downstream refining."
    ),
    "Imperial Oil": (
        "Calgary-based integrated oil company majority owned by ExxonMobil. "
        "Operates Cold Lake and Kearl oil sands, Strathcona and Sarnia "
        "refineries, and the ESSO retail brand."
    ),
    "Tourmaline Oil": (
        "Calgary-based natural gas producer focused on the Western Canadian "
        "Sedimentary Basin. Canada's largest natural gas producer by output."
    ),
    "ARC Resources": (
        "Calgary-based pure-play Montney natural gas and condensate producer."
    ),
    "TC Energy": (
        "Calgary-based midstream energy infrastructure company operating "
        "natural gas pipelines (NGTL, Coastal GasLink), liquids pipelines "
        "(Keystone), and a growing power generation portfolio."
    ),
    "Enbridge": (
        "Calgary-based midstream energy company operating the largest crude "
        "oil pipeline system in North America (Mainline), substantial natural "
        "gas pipelines and distribution, and growing renewable generation."
    ),
    "Pembina Pipeline": (
        "Calgary-based midstream services company. Operates conventional "
        "pipelines, oil sands logistics, NGL fractionation, and a Redwater-"
        "centred natural gas liquids hub."
    ),
    "AltaGas": (
        "Calgary-based midstream and utilities company. Owns natural gas "
        "distribution utilities in the US Mid-Atlantic and operates the Ridley "
        "Island propane export terminal in British Columbia."
    ),
    "Trans Mountain Corporation": (
        "Crown corporation operating the Trans Mountain Pipeline from Alberta "
        "to Burnaby, BC. Completed a $34B expansion adding 590,000 bpd of "
        "capacity in 2024."
    ),

    # ---- Mining ----
    "Teck Resources": (
        "Vancouver-based diversified mining company. Major producer of "
        "metallurgical coal (now spun off as Elk Valley Resources), copper, "
        "and zinc, with operations in BC, Alberta, Chile, and Peru."
    ),
    "Barrick Gold": (
        "Toronto-based senior gold and copper producer. Operates assets "
        "across North America, South America, and Africa. Joint venture "
        "partner with Newmont in Nevada Gold Mines."
    ),
    "Newmont Canada": (
        "Canadian operations of Newmont, the world's largest gold producer. "
        "Operates the Porcupine, Musselwhite, and Brucejack mines in Ontario "
        "and BC."
    ),
    "Cameco Corporation": (
        "Saskatoon-based uranium producer, one of the world's largest. "
        "Operates the McArthur River, Cigar Lake, and Key Lake assets in "
        "northern Saskatchewan plus the Port Hope conversion facility."
    ),
    "Lundin Mining": (
        "Toronto-based diversified base metals miner. Operates copper, zinc, "
        "and nickel mines including Eagle Mine (Michigan), Candelaria (Chile), "
        "and Neves-Corvo (Portugal)."
    ),
    "Agnico Eagle Mines": (
        "Toronto-based senior gold producer with operations across Quebec, "
        "Ontario, Nunavut (Meadowbank, Meliadine), Finland, Mexico, and "
        "Australia."
    ),

    # ---- Utilities ----
    "Hydro One": (
        "Ontario's largest electricity transmission and distribution utility. "
        "Operates ~30,000 km of high-voltage transmission across the province "
        "and serves 1.5M+ customers."
    ),
    "BC Hydro": (
        "Crown corporation operating British Columbia's electricity system, "
        "predominantly hydroelectric. Operating Site C, a $16B 1,100 MW "
        "Peace River dam project."
    ),
    "Manitoba Hydro": (
        "Crown corporation providing electricity and natural gas across "
        "Manitoba. Operates 15+ hydroelectric stations including Keeyask."
    ),
    "SaskPower": (
        "Saskatchewan Crown utility. Operates coal, natural gas, hydro, and "
        "wind generation, plus the Boundary Dam carbon capture facility."
    ),
    "Ontario Power Generation": (
        "Provincial Crown power generator operating Darlington and Pickering "
        "nuclear, hydroelectric, and gas assets. Leading the BWRX-300 small "
        "modular reactor project at Darlington."
    ),
    "Bruce Power": (
        "Operates the eight-unit Bruce Nuclear Generating Station near "
        "Kincardine, Ontario - the world's largest operating nuclear facility "
        "by output. Executing the Major Component Replacement refurbishment "
        "program."
    ),
    "ATCO": (
        "Calgary-based diversified utilities and infrastructure company. "
        "Operates natural gas and electricity distribution in Alberta and "
        "structures, logistics, and energy services globally."
    ),
    "Hydro-Québec": (
        "Quebec's vertically-integrated public electric utility. Operates "
        "63 hydroelectric stations and 735 kV transmission - the largest "
        "hydroelectric utility in North America by capacity."
    ),
    "Nalcor Energy": (
        "Newfoundland and Labrador Crown utility (since amalgamated under "
        "NL Hydro). Operates Muskrat Falls hydroelectric and the Maritime "
        "Link to Nova Scotia."
    ),
}
