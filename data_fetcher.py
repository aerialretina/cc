"""
Data fetcher – pulls market data from FRED and Yahoo Finance.
"""

import os
import logging
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from fredapi import Fred
from dotenv import load_dotenv

import config

load_dotenv()
log = logging.getLogger(__name__)


def _fred_client() -> Fred | None:
    key = os.getenv("FRED_API_KEY")
    if not key or key.startswith("your_"):
        log.warning("FRED_API_KEY not set – FRED data will be unavailable")
        return None
    return Fred(api_key=key)


# ------------------------------------------------------------------
# FRED data
# ------------------------------------------------------------------

def fetch_fred_series(series_map: dict[str, str] | None = None,
                      lookback_days: int = 90) -> pd.DataFrame:
    """Fetch multiple FRED series into a single DataFrame.

    Returns a DataFrame indexed by date with one column per series name.
    """
    client = _fred_client()
    if client is None:
        return pd.DataFrame()

    if series_map is None:
        series_map = config.FRED_SERIES

    end = datetime.today()
    start = end - timedelta(days=lookback_days)
    frames: dict[str, pd.Series] = {}

    for name, series_id in series_map.items():
        try:
            s = client.get_series(series_id, observation_start=start,
                                  observation_end=end)
            frames[name] = s
        except Exception as exc:
            log.warning("Failed to fetch FRED series %s (%s): %s",
                        name, series_id, exc)

    if not frames:
        return pd.DataFrame()

    df = pd.DataFrame(frames)
    df.index.name = "date"
    return df


# ------------------------------------------------------------------
# Yahoo Finance data
# ------------------------------------------------------------------

def fetch_yf_history(tickers: dict[str, str] | None = None,
                     period: str = "3mo") -> pd.DataFrame:
    """Fetch closing prices for a dict of {label: ticker} via yfinance.

    Returns a DataFrame indexed by date with one column per label.
    """
    if tickers is None:
        tickers = config.YF_TICKERS

    frames: dict[str, pd.Series] = {}

    for label, ticker in tickers.items():
        try:
            hist = yf.Ticker(ticker).history(period=period)
            if hist.empty:
                log.warning("No data returned for %s (%s)", label, ticker)
                continue
            frames[label] = hist["Close"]
        except Exception as exc:
            log.warning("Failed to fetch YF ticker %s (%s): %s",
                        label, ticker, exc)

    if not frames:
        return pd.DataFrame()

    df = pd.DataFrame(frames)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "date"
    return df


# ------------------------------------------------------------------
# Convenience wrapper
# ------------------------------------------------------------------

def fetch_all() -> dict[str, pd.DataFrame]:
    """Return a dict with keys 'fred' and 'yf', each a DataFrame."""
    log.info("Fetching FRED data …")
    fred_df = fetch_fred_series()
    log.info("Fetching Yahoo Finance data …")
    yf_df = fetch_yf_history()
    return {"fred": fred_df, "yf": yf_df}
