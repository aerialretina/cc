"""
Analysis engine – detects significant moves, divergences, and regime shifts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd

import config

log = logging.getLogger(__name__)


@dataclass
class Signal:
    """A single notable observation."""
    asset: str
    asset_class: str
    metric: str          # e.g. "1d_change", "1w_change"
    value: float         # the actual change
    threshold: float     # the threshold it exceeded
    description: str     # human-readable note
    severity: int = 1    # 1 = notable, 2 = significant, 3 = extreme


@dataclass
class AnalysisResult:
    """Container for all analysis outputs."""
    as_of: str
    signals: list[Signal] = field(default_factory=list)
    data_table: pd.DataFrame | None = None
    yield_curve_bps: float | None = None   # 10Y − 2Y spread


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return ((current - previous) / abs(previous)) * 100


def _bps_change(current: float, previous: float) -> float:
    return (current - previous) * 100  # yields stored as % in data


def _get_prior_value(series: pd.Series, days_back: int) -> float | None:
    """Return the closest available value approximately `days_back` ago."""
    if series.dropna().empty:
        return None
    target = series.index.max() - timedelta(days=days_back)
    mask = series.index <= target
    prior = series.loc[mask].dropna()
    if prior.empty:
        return None
    return float(prior.iloc[-1])


def _classify_asset(label: str) -> str:
    for cls, members in config.ASSET_CLASSES.items():
        if label in members:
            return cls
    return "other"


def _severity(ratio: float) -> int:
    """Map |change / threshold| to severity 1-3."""
    if ratio >= 2.0:
        return 3
    if ratio >= 1.3:
        return 2
    return 1


# ------------------------------------------------------------------
# Core analysis
# ------------------------------------------------------------------

def analyze_market_data(yf_df: pd.DataFrame) -> AnalysisResult:
    """Scan Yahoo Finance data for threshold-exceeding moves."""
    result = AnalysisResult(as_of=datetime.utcnow().strftime("%Y-%m-%d"))
    if yf_df.empty:
        return result

    latest_row = yf_df.iloc[-1]
    summary_rows: list[dict] = []

    for label in yf_df.columns:
        series = yf_df[label].dropna()
        if series.empty:
            continue

        current = float(series.iloc[-1])
        asset_class = _classify_asset(label)

        row: dict = {"Asset": label, "Current": round(current, 2)}

        for window_name, days in config.LOOKBACK.items():
            prior = _get_prior_value(series, days)
            if prior is None:
                row[f"Δ {window_name}"] = None
                continue

            if asset_class == "rates":
                change = _bps_change(current, prior)
                row[f"Δ {window_name}"] = f"{change:+.1f} bps"
                # Check thresholds
                th_key = f"yield_{window_name}_bps"
                th = config.THRESHOLDS.get(th_key)
                if th and abs(change) > th:
                    result.signals.append(Signal(
                        asset=label,
                        asset_class=asset_class,
                        metric=f"{window_name}_change",
                        value=change,
                        threshold=th,
                        description=f"{label} moved {change:+.1f} bps over {window_name} (threshold ±{th})",
                        severity=_severity(abs(change) / th),
                    ))
            else:
                change = _pct_change(current, prior)
                row[f"Δ {window_name}"] = f"{change:+.2f}%"
                th_key = f"{asset_class}_{window_name}_pct"
                th = config.THRESHOLDS.get(th_key)
                if th and abs(change) > th:
                    result.signals.append(Signal(
                        asset=label,
                        asset_class=asset_class,
                        metric=f"{window_name}_change",
                        value=change,
                        threshold=th,
                        description=f"{label} moved {change:+.2f}% over {window_name} (threshold ±{th}%)",
                        severity=_severity(abs(change) / th),
                    ))

        summary_rows.append(row)

    result.data_table = pd.DataFrame(summary_rows)

    # Yield curve spread
    if "US 10Y Yield" in yf_df.columns and "US 2Y Yield" in yf_df.columns:
        y10 = yf_df["US 10Y Yield"].dropna()
        y2 = yf_df["US 2Y Yield"].dropna()
        if not y10.empty and not y2.empty:
            result.yield_curve_bps = round((float(y10.iloc[-1]) - float(y2.iloc[-1])) * 100, 1)

    # Sort signals by severity descending
    result.signals.sort(key=lambda s: s.severity, reverse=True)

    return result


# ------------------------------------------------------------------
# Divergence detection
# ------------------------------------------------------------------

def detect_divergences(yf_df: pd.DataFrame, window: int = 7) -> list[str]:
    """Identify notable cross-market divergences over `window` days."""
    notes: list[str] = []
    if yf_df.empty:
        return notes

    def _recent_return(label: str) -> float | None:
        if label not in yf_df.columns:
            return None
        s = yf_df[label].dropna()
        prior = _get_prior_value(s, window)
        if prior is None:
            return None
        return _pct_change(float(s.iloc[-1]), prior)

    # Stocks up / bonds selling off (risk-on) vs stocks down / bonds bid (risk-off)
    sp_ret = _recent_return("S&P 500")
    tnx_chg = _recent_return("US 10Y Yield")
    if sp_ret is not None and tnx_chg is not None:
        if sp_ret > 1.5 and tnx_chg < -1.0:
            notes.append("Divergence: equities rallying while yields fall — possible flight-to-quality mixed signal")
        if sp_ret < -1.5 and tnx_chg > 1.0:
            notes.append("Divergence: equities falling while yields rise — possible stagflation concern")

    # Gold vs USD
    gold_ret = _recent_return("Gold")
    dxy_ret = _recent_return("DXY")
    if gold_ret is not None and dxy_ret is not None:
        if gold_ret > 2.0 and dxy_ret > 1.0:
            notes.append("Divergence: gold and USD both rising — unusual risk-haven demand")

    # Copper vs equities (growth proxy)
    cu_ret = _recent_return("Copper")
    if cu_ret is not None and sp_ret is not None:
        if cu_ret < -3.0 and sp_ret > 1.0:
            notes.append("Divergence: copper weak while equities strong — industrial demand may be softening")

    return notes
