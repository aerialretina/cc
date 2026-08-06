"""
Central configuration for the macro monitoring assistant.

Regional focus: EU (Eurozone), UK, India
Also retains core global/US data for cross-reference.
"""

# ---------------------------------------------------------------------------
# FRED series IDs (US baseline + some international)
# ---------------------------------------------------------------------------
FRED_SERIES = {
    # US Treasury yields (baseline reference)
    "US10Y": "DGS10",
    "US2Y": "DGS2",
    "US3M": "DGS3MO",
    # Fed Funds effective rate
    "FED_FUNDS": "DFF",
    # CPI YoY
    "CPI_YOY": "CPIAUCSL",
    # Unemployment rate
    "UNEMPLOYMENT": "UNRATE",
    # ISM Manufacturing PMI
    "ISM_MFG": "MANEMP",
    # Initial jobless claims
    "JOBLESS_CLAIMS": "ICSA",
    # Real GDP growth (quarterly, annualized)
    "REAL_GDP": "A191RL1Q225SBEA",
    # Breakeven inflation 10Y
    "BREAKEVEN_10Y": "T10YIE",
    # US Dollar Index (proxy via trade-weighted broad)
    "USD_TWI": "DTWEXBGS",
}

# EU-specific FRED series
FRED_SERIES_EU = {
    "EU_HICP": "CP0000EZ19M086NEST",           # Eurozone HICP all items
    "EU_CORE_HICP": "CCRETT01EZM661N",         # Eurozone core HICP
    "GERMAN_10Y": "IRLTLT01DEM156N",           # German 10Y government bond
    "EU_UNEMPLOYMENT": "LRHUTTTTEZM156S",      # Eurozone unemployment rate
    "ECB_RATE": "ECBDFR",                      # ECB deposit facility rate
    "GERMAN_PPI": "PIEAMP02DEM659N",           # German PPI
    "EU_M3": "MABMM301EZM189S",               # Eurozone M3 money supply
    "EU_RETAIL_SALES": "SLRTTO02EZM659S",      # Eurozone retail trade
}

# UK-specific FRED series
FRED_SERIES_UK = {
    "UK_CPI": "CPALTT01GBM659N",              # UK CPI all items
    "UK_10Y": "IRLTLT01GBM156N",              # UK 10Y gilt yield
    "UK_UNEMPLOYMENT": "LRHUTTTTGBM156S",     # UK unemployment rate
    "BOE_RATE": "BOGZ1FL072052006Q",          # BoE policy rate (proxy)
    "UK_RETAIL_SALES": "SLRTTO02GBM659S",     # UK retail sales
    "UK_PPI": "PIEAMP02GBM659N",              # UK PPI
}

# India-specific FRED series
FRED_SERIES_INDIA = {
    "INDIA_CPI": "CPALTT01INM659N",           # India CPI
    "INDIA_WPI": "PIEAMP02INM659N",           # India WPI (wholesale prices)
    "INDIA_10Y": "IRLTLT01INM156N",           # India 10Y government bond
    "RBI_RATE": "INTDSRINM193N",              # RBI repo rate (discount)
}

# ---------------------------------------------------------------------------
# Yahoo Finance tickers — Regional focus
# ---------------------------------------------------------------------------

# EU-region tickers
YF_TICKERS_EU = {
    # Equity indices
    "Euro Stoxx 50": "^STOXX50E",
    "STOXX 600": "^STOXX",
    "DAX": "^GDAXI",
    "CAC 40": "^FCHI",
    "FTSE MIB": "FTSEMIB.MI",
    "IBEX 35": "^IBEX",
    "STOXX Banks": "SX7E.S",
    # Sovereign bonds (yield proxies via ETFs)
    "German 10Y ETF": "EXX6.DE",          # iShares German Govt Bond ETF
    "Italian BTP ETF": "IITB.L",          # iShares Italy Govt Bond ETF
    # Currencies
    "EUR/USD": "EURUSD=X",
    "EUR/GBP": "EURGBP=X",
    "EUR/CHF": "EURCHF=X",
    # Energy
    "Brent Crude": "BZ=F",
    "EU Natural Gas": "TTF=F",            # TTF Natural Gas
}

# UK-region tickers
YF_TICKERS_UK = {
    # Equity indices
    "FTSE 100": "^FTSE",
    "FTSE 250": "^MCX",
    # Gilts (via ETFs)
    "UK Gilt ETF": "IGLT.L",              # iShares Core UK Gilts
    "UK Short Gilt": "ERNS.L",            # Short-dated gilt ETF
    "UK IL Gilt ETF": "INXG.L",           # Inflation-linked gilt ETF
    # Currencies
    "GBP/USD": "GBPUSD=X",
    "GBP/EUR": "GBPEUR=X",
    # Housing proxy
    "UK Homebuilders": "BDEV.L",          # Barratt (proxy for housing)
}

# India-region tickers
YF_TICKERS_INDIA = {
    # Equity indices
    "NIFTY 50": "^NSEI",
    "NIFTY Bank": "^NSEBANK",
    "BSE Sensex": "^BSESN",
    "NIFTY IT": "^CNXIT",
    # Currencies
    "USD/INR": "INR=X",
    "EUR/INR": "EURINR=X",
    # Commodity proxies important for India
    "WTI Crude": "CL=F",
    "Gold": "GC=F",
    # India-specific ETFs (US-listed India exposure)
    "India ETF (INDA)": "INDA",
    "India Small-Cap ETF": "SMIN",
}

# Global/cross-regional reference tickers
YF_TICKERS_GLOBAL = {
    "S&P 500": "^GSPC",
    "DXY": "DX-Y.NYB",
    "VIX": "^VIX",
    "US 10Y Yield": "^TNX",
    "US 2Y Yield": "^IRX",
    "Copper": "HG=F",
    "WTI Crude": "CL=F",
    "Gold": "GC=F",
}

# Combined for convenience
YF_TICKERS = {**YF_TICKERS_EU, **YF_TICKERS_UK, **YF_TICKERS_INDIA, **YF_TICKERS_GLOBAL}

# ---------------------------------------------------------------------------
# Thresholds for flagging significant moves
# ---------------------------------------------------------------------------
THRESHOLDS = {
    # Yield moves (absolute bps change)
    "yield_1d_bps": 8,
    "yield_1w_bps": 20,
    # Equity moves (% change)
    "equity_1d_pct": 1.5,
    "equity_1w_pct": 3.0,
    # Currency moves (% change)
    "fx_1d_pct": 0.8,
    "fx_1w_pct": 2.0,
    # Commodity moves (% change)
    "commodity_1d_pct": 2.5,
    "commodity_1w_pct": 5.0,
    # Spread moves (bps change — for sovereign spreads)
    "spread_1d_bps": 10,
    "spread_1w_bps": 25,
    # Volatility
    "vix_1d_pct": 10.0,
    "vix_1w_pct": 20.0,
}

# Thresholds for >2 standard deviation alert (used in regime detection)
EXTREME_MOVE_SIGMA = 2.0

# ---------------------------------------------------------------------------
# Lookback windows (calendar days) for comparison
# ---------------------------------------------------------------------------
LOOKBACK = {
    "1d": 1,
    "1w": 7,
    "1m": 30,
}

# ---------------------------------------------------------------------------
# Regional asset class groupings
# ---------------------------------------------------------------------------

ASSET_CLASSES_EU = {
    "equities": ["Euro Stoxx 50", "STOXX 600", "DAX", "CAC 40", "FTSE MIB",
                  "IBEX 35", "STOXX Banks"],
    "bonds": ["German 10Y ETF", "Italian BTP ETF"],
    "currencies": ["EUR/USD", "EUR/GBP", "EUR/CHF"],
    "commodities": ["Brent Crude", "EU Natural Gas"],
}

ASSET_CLASSES_UK = {
    "equities": ["FTSE 100", "FTSE 250"],
    "bonds": ["UK Gilt ETF", "UK Short Gilt", "UK IL Gilt ETF"],
    "currencies": ["GBP/USD", "GBP/EUR"],
    "housing": ["UK Homebuilders"],
}

ASSET_CLASSES_INDIA = {
    "equities": ["NIFTY 50", "NIFTY Bank", "BSE Sensex", "NIFTY IT"],
    "currencies": ["USD/INR", "EUR/INR"],
    "commodities": ["WTI Crude", "Gold"],
    "etfs": ["India ETF (INDA)", "India Small-Cap ETF"],
}

ASSET_CLASSES_GLOBAL = {
    "equities": ["S&P 500"],
    "currencies": ["DXY"],
    "commodities": ["WTI Crude", "Gold", "Copper"],
    "rates": ["US 10Y Yield", "US 2Y Yield"],
    "volatility": ["VIX"],
}

# Combined lookup for backward compatibility
ASSET_CLASSES = {}
for _region_map in [ASSET_CLASSES_EU, ASSET_CLASSES_UK, ASSET_CLASSES_INDIA, ASSET_CLASSES_GLOBAL]:
    for _cls, _members in _region_map.items():
        ASSET_CLASSES.setdefault(_cls, []).extend(_members)

# ---------------------------------------------------------------------------
# Region definitions (for iterating and labeling)
# ---------------------------------------------------------------------------
REGIONS = {
    "EU": {
        "label": "EU (Eurozone)",
        "fred_series": FRED_SERIES_EU,
        "yf_tickers": YF_TICKERS_EU,
        "asset_classes": ASSET_CLASSES_EU,
        "key_equity": "Euro Stoxx 50",
        "key_bond_etf": "German 10Y ETF",
        "key_fx": "EUR/USD",
        "key_rate_fred": "ECB_RATE",
        "key_cpi_fred": "EU_HICP",
    },
    "UK": {
        "label": "UK",
        "fred_series": FRED_SERIES_UK,
        "yf_tickers": YF_TICKERS_UK,
        "asset_classes": ASSET_CLASSES_UK,
        "key_equity": "FTSE 100",
        "key_bond_etf": "UK Gilt ETF",
        "key_fx": "GBP/USD",
        "key_rate_fred": "BOE_RATE",
        "key_cpi_fred": "UK_CPI",
    },
    "India": {
        "label": "India",
        "fred_series": FRED_SERIES_INDIA,
        "yf_tickers": YF_TICKERS_INDIA,
        "asset_classes": ASSET_CLASSES_INDIA,
        "key_equity": "NIFTY 50",
        "key_bond_etf": None,
        "key_fx": "USD/INR",
        "key_rate_fred": "RBI_RATE",
        "key_cpi_fred": "INDIA_CPI",
    },
}

# ---------------------------------------------------------------------------
# Regime classification labels
# ---------------------------------------------------------------------------
GROWTH_STAGES = ["contraction", "early_recovery", "expansion", "late_cycle", "slowdown"]
INFLATION_TRAJECTORIES = ["falling", "bottoming", "rising", "peaking", "sticky"]
POLICY_STANCES = ["accommodative", "neutral", "restrictive"]
STABILITY_RISK_LEVELS = ["low", "moderate", "elevated", "high"]
EXTERNAL_VULNERABILITY = ["low", "moderate", "elevated", "high"]

# Traffic light mapping for regime display
TRAFFIC_LIGHTS = {
    "green": ["expansion", "early_recovery", "falling", "bottoming",
              "accommodative", "low"],
    "amber": ["late_cycle", "slowdown", "rising", "sticky",
              "neutral", "moderate", "elevated"],
    "red": ["contraction", "peaking", "restrictive", "high"],
}

# ---------------------------------------------------------------------------
# Focus areas text (for briefing watch section)
# ---------------------------------------------------------------------------
FOCUS_AREAS = {
    "EU": [
        "Peripheral spread widening (Italy/Spain vs Bunds)",
        "ECB terminal rate debates and QT pace",
        "German factory orders and manufacturing PMI trends",
        "Energy dependency metrics and natural gas prices",
        "EU fiscal rules compliance and political stability",
    ],
    "UK": [
        "Stagflation risk: inflation persistence vs growth weakness",
        "Fiscal credibility and gilt market stability",
        "Services inflation stickiness (70% of economy)",
        "Housing market trajectory and mortgage impact",
        "Brexit trade flow impacts and labor market tightness",
    ],
    "India": [
        "Monsoon season impacts on food inflation",
        "Oil price sensitivity and current account effects",
        "RBI forex intervention and reserve adequacy",
        "GST collection trends as growth proxy",
        "FDI flows and reform momentum indicators",
    ],
}
