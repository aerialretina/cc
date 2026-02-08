"""
Central configuration for the macro monitoring assistant.
"""

# ---------------------------------------------------------------------------
# FRED series IDs
# ---------------------------------------------------------------------------
FRED_SERIES = {
    # Treasury yields
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

# ---------------------------------------------------------------------------
# Yahoo Finance tickers for real-time / delayed market data
# ---------------------------------------------------------------------------
YF_TICKERS = {
    # Equity indices
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Dow Jones": "^DJI",
    "Euro Stoxx 50": "^STOXX50E",
    "Nikkei 225": "^N225",
    "FTSE 100": "^FTSE",
    "Shanghai Composite": "000001.SS",
    # Currencies
    "DXY": "DX-Y.NYB",
    "EUR/USD": "EURUSD=X",
    "USD/JPY": "USDJPY=X",
    "GBP/USD": "GBPUSD=X",
    "USD/CNY": "USDCNY=X",
    # Commodities
    "WTI Crude": "CL=F",
    "Gold": "GC=F",
    "Copper": "HG=F",
    "Silver": "SI=F",
    # Bonds / Rates
    "US 10Y Yield": "^TNX",
    "US 2Y Yield": "^IRX",  # 13-week proxy; 2Y not directly available
}

# ---------------------------------------------------------------------------
# Thresholds for flagging significant moves (in percentage points or %)
# ---------------------------------------------------------------------------
THRESHOLDS = {
    # Yield moves (absolute bps change)
    "yield_1d_bps": 8,       # flag >8 bps daily move
    "yield_1w_bps": 20,      # flag >20 bps weekly move
    # Equity moves (% change)
    "equity_1d_pct": 1.5,    # flag >1.5% daily move
    "equity_1w_pct": 3.0,    # flag >3% weekly move
    # Currency moves (% change)
    "fx_1d_pct": 0.8,        # flag >0.8% daily move
    "fx_1w_pct": 2.0,        # flag >2% weekly move
    # Commodity moves (% change)
    "commodity_1d_pct": 2.5,  # flag >2.5% daily move
    "commodity_1w_pct": 5.0,  # flag >5% weekly move
}

# ---------------------------------------------------------------------------
# Lookback windows (calendar days) for comparison
# ---------------------------------------------------------------------------
LOOKBACK = {
    "1d": 1,
    "1w": 7,
    "1m": 30,
}

# ---------------------------------------------------------------------------
# Asset class groupings (used by the analysis engine)
# ---------------------------------------------------------------------------
ASSET_CLASSES = {
    "equities": ["S&P 500", "NASDAQ", "Dow Jones", "Euro Stoxx 50", "Nikkei 225",
                  "FTSE 100", "Shanghai Composite"],
    "currencies": ["DXY", "EUR/USD", "USD/JPY", "GBP/USD", "USD/CNY"],
    "commodities": ["WTI Crude", "Gold", "Copper", "Silver"],
    "rates": ["US 10Y Yield", "US 2Y Yield"],
}
