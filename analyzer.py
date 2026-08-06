"""
Analysis engine – detects significant moves, divergences, regime shifts,
and cross-regional macro dynamics for EU, UK, and India.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

import config

log = logging.getLogger(__name__)


# ===================================================================
# Data classes
# ===================================================================

@dataclass
class Signal:
    """A single notable observation."""
    asset: str
    asset_class: str
    region: str
    metric: str          # e.g. "1d_change", "1w_change"
    value: float         # the actual change
    threshold: float     # the threshold it exceeded
    description: str     # human-readable note
    severity: int = 1    # 1 = notable, 2 = significant, 3 = extreme


@dataclass
class RegimeAssessment:
    """Regime classification for a single region."""
    region: str
    growth_stage: str           # contraction / early_recovery / expansion / late_cycle / slowdown
    inflation_trajectory: str   # falling / bottoming / rising / peaking / sticky
    policy_stance: str          # accommodative / neutral / restrictive
    stability_risk: str         # low / moderate / elevated / high
    external_vulnerability: str # low / moderate / elevated / high
    notes: list[str] = field(default_factory=list)

    def traffic_light(self, dimension: str) -> str:
        val = getattr(self, dimension, None)
        if val is None:
            return "grey"
        for color, values in config.TRAFFIC_LIGHTS.items():
            if val in values:
                return color
        return "grey"


@dataclass
class DivergenceAlert:
    """Cross-regional divergence detection."""
    category: str       # e.g. "policy", "growth", "currency", "contagion"
    regions: list[str]
    description: str
    severity: int = 1   # 1 = notable, 2 = significant


@dataclass
class RegionalAnalysis:
    """Container for a single region's analysis."""
    region: str
    signals: list[Signal] = field(default_factory=list)
    data_table: pd.DataFrame | None = None
    regime: RegimeAssessment | None = None
    executive_bullets: list[str] = field(default_factory=list)


@dataclass
class CrossRegionalResult:
    """Container for the full multi-region analysis."""
    as_of: str
    regions: dict[str, RegionalAnalysis] = field(default_factory=dict)
    divergence_alerts: list[DivergenceAlert] = field(default_factory=list)
    yield_curve_us_bps: float | None = None
    forward_indicators: list[str] = field(default_factory=list)
    cross_implications: list[str] = field(default_factory=list)


# ===================================================================
# Helpers
# ===================================================================

def _pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return ((current - previous) / abs(previous)) * 100


def _bps_change(current: float, previous: float) -> float:
    return (current - previous) * 100  # yields stored as % in data


def _get_prior_value(series: pd.Series, days_back: int) -> float | None:
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


def _classify_asset_regional(label: str, region: str) -> str:
    region_classes = config.REGIONS.get(region, {}).get("asset_classes", {})
    for cls, members in region_classes.items():
        if label in members:
            return cls
    return _classify_asset(label)


def _severity(ratio: float) -> int:
    if ratio >= 2.0:
        return 3
    if ratio >= 1.3:
        return 2
    return 1


def _compute_rolling_std(series: pd.Series, window: int = 60) -> float | None:
    """Compute rolling standard deviation for z-score calculation."""
    if len(series.dropna()) < window:
        return None
    return float(series.dropna().pct_change().rolling(window).std().iloc[-1])


def _z_score_move(series: pd.Series, days_back: int = 1, window: int = 60) -> float | None:
    """Calculate z-score of recent move vs historical rolling volatility."""
    s = series.dropna()
    if len(s) < window + days_back:
        return None
    returns = s.pct_change().dropna()
    if len(returns) < window:
        return None
    recent_return = float(returns.iloc[-1]) if days_back == 1 else float(
        _pct_change(float(s.iloc[-1]), float(s.iloc[-days_back])) / 100
    )
    rolling_std = float(returns.rolling(window).std().iloc[-1])
    if rolling_std == 0:
        return None
    return recent_return / rolling_std


# ===================================================================
# Core regional analysis
# ===================================================================

def analyze_region(yf_df: pd.DataFrame, region: str) -> RegionalAnalysis:
    """Analyze market data for a specific region."""
    result = RegionalAnalysis(region=region)
    if yf_df.empty:
        return result

    summary_rows: list[dict] = []
    extreme_moves: list[str] = []

    for label in yf_df.columns:
        series = yf_df[label].dropna()
        if series.empty:
            continue

        current = float(series.iloc[-1])
        asset_class = _classify_asset_regional(label, region)

        row: dict = {"Asset": label, "Class": asset_class, "Current": round(current, 2)}

        for window_name, days in config.LOOKBACK.items():
            prior = _get_prior_value(series, days)
            if prior is None:
                row[f"Δ {window_name}"] = None
                continue

            if asset_class == "rates":
                change = _bps_change(current, prior)
                row[f"Δ {window_name}"] = f"{change:+.1f} bps"
                th_key = f"yield_{window_name}_bps"
                th = config.THRESHOLDS.get(th_key)
                if th and abs(change) > th:
                    result.signals.append(Signal(
                        asset=label, asset_class=asset_class, region=region,
                        metric=f"{window_name}_change", value=change,
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
                        asset=label, asset_class=asset_class, region=region,
                        metric=f"{window_name}_change", value=change,
                        threshold=th,
                        description=f"{label} moved {change:+.2f}% over {window_name} (threshold ±{th}%)",
                        severity=_severity(abs(change) / th),
                    ))

        # Check for >2 sigma moves (extreme flag)
        z = _z_score_move(series)
        if z is not None and abs(z) >= config.EXTREME_MOVE_SIGMA:
            extreme_moves.append(
                f"{label}: {z:+.1f}σ daily move (extreme)"
            )
            row["Z-Score"] = f"{z:+.1f}σ"
        else:
            row["Z-Score"] = ""

        summary_rows.append(row)

    result.data_table = pd.DataFrame(summary_rows) if summary_rows else None
    result.signals.sort(key=lambda s: s.severity, reverse=True)

    # Build executive bullets (top 3 per region)
    if extreme_moves:
        result.executive_bullets.append(
            f"EXTREME: {'; '.join(extreme_moves[:2])}"
        )
    top_signals = result.signals[:3]
    for sig in top_signals:
        direction = "higher" if sig.value > 0 else "lower"
        result.executive_bullets.append(
            f"{sig.asset} moved sharply {direction} ({sig.description})"
        )
    if not result.executive_bullets:
        result.executive_bullets.append("No threshold-exceeding moves detected.")

    # Trim to 3 bullets
    result.executive_bullets = result.executive_bullets[:3]

    return result


# ===================================================================
# Regime classification
# ===================================================================

def classify_regime(yf_df: pd.DataFrame, fred_df: pd.DataFrame,
                    region: str) -> RegimeAssessment:
    """Classify the macro regime for a region based on available data."""
    regime = RegimeAssessment(
        region=region,
        growth_stage="expansion",
        inflation_trajectory="sticky",
        policy_stance="restrictive",
        stability_risk="moderate",
        external_vulnerability="moderate",
    )

    region_conf = config.REGIONS.get(region, {})

    # --- Growth stage ---
    key_equity = region_conf.get("key_equity")
    if key_equity and key_equity in yf_df.columns:
        eq = yf_df[key_equity].dropna()
        if len(eq) >= 30:
            ret_1m = _pct_change(float(eq.iloc[-1]),
                                 float(eq.iloc[-min(30, len(eq))]))
            ret_1w = _pct_change(float(eq.iloc[-1]),
                                 float(eq.iloc[-min(7, len(eq))]))
            if ret_1m < -5:
                regime.growth_stage = "contraction"
                regime.notes.append(f"{key_equity} down {ret_1m:.1f}% over 1m → contraction signal")
            elif ret_1m < -2:
                regime.growth_stage = "slowdown"
                regime.notes.append(f"{key_equity} weak at {ret_1m:.1f}% over 1m")
            elif ret_1m > 5:
                regime.growth_stage = "expansion"
                regime.notes.append(f"{key_equity} strong at {ret_1m:+.1f}% over 1m")
            elif ret_1w > 2 and ret_1m < 0:
                regime.growth_stage = "early_recovery"
                regime.notes.append(f"{key_equity} showing recovery signals")
            else:
                regime.growth_stage = "late_cycle"
                regime.notes.append(f"{key_equity} at {ret_1m:+.1f}% over 1m → late cycle")

    # --- Inflation trajectory ---
    cpi_key = region_conf.get("key_cpi_fred")
    if cpi_key and cpi_key in fred_df.columns:
        cpi = fred_df[cpi_key].dropna()
        if len(cpi) >= 3:
            recent = cpi.iloc[-3:]
            if recent.is_monotonic_decreasing:
                regime.inflation_trajectory = "falling"
                regime.notes.append("CPI/HICP trending down")
            elif recent.is_monotonic_increasing:
                regime.inflation_trajectory = "rising"
                regime.notes.append("CPI/HICP trending up")
            else:
                diff = float(recent.iloc[-1]) - float(recent.iloc[0])
                if abs(diff) < 0.3:
                    regime.inflation_trajectory = "sticky"
                    regime.notes.append("CPI/HICP stuck in narrow range")
                elif diff > 0:
                    regime.inflation_trajectory = "peaking"
                    regime.notes.append("CPI/HICP near peak with mixed signals")
                else:
                    regime.inflation_trajectory = "bottoming"
                    regime.notes.append("CPI/HICP near trough")

    # --- Policy stance ---
    rate_key = region_conf.get("key_rate_fred")
    if rate_key and rate_key in fred_df.columns:
        rates = fred_df[rate_key].dropna()
        if not rates.empty:
            latest_rate = float(rates.iloc[-1])
            if latest_rate > 4.0:
                regime.policy_stance = "restrictive"
                regime.notes.append(f"Policy rate at {latest_rate:.2f}% → restrictive")
            elif latest_rate > 2.0:
                regime.policy_stance = "neutral"
                regime.notes.append(f"Policy rate at {latest_rate:.2f}% → neutral")
            else:
                regime.policy_stance = "accommodative"
                regime.notes.append(f"Policy rate at {latest_rate:.2f}% → accommodative")

    # --- Financial stability risk ---
    # EU: check bank index and spreads
    if region == "EU":
        if "STOXX Banks" in yf_df.columns:
            banks = yf_df["STOXX Banks"].dropna()
            if len(banks) >= 30:
                ret = _pct_change(float(banks.iloc[-1]),
                                  float(banks.iloc[-min(30, len(banks))]))
                if ret < -10:
                    regime.stability_risk = "high"
                    regime.notes.append(f"STOXX Banks down {ret:.1f}% → elevated banking stress")
                elif ret < -5:
                    regime.stability_risk = "elevated"
                    regime.notes.append(f"STOXX Banks weakening at {ret:.1f}%")

    # UK: check gilt market
    elif region == "UK":
        if "UK Gilt ETF" in yf_df.columns:
            gilts = yf_df["UK Gilt ETF"].dropna()
            if len(gilts) >= 30:
                ret = _pct_change(float(gilts.iloc[-1]),
                                  float(gilts.iloc[-min(30, len(gilts))]))
                if ret < -5:
                    regime.stability_risk = "high"
                    regime.notes.append(f"Gilt ETF down {ret:.1f}% → gilt stress")
                elif ret < -2:
                    regime.stability_risk = "elevated"
                    regime.notes.append(f"Gilt ETF weakening at {ret:.1f}%")

    # India: check FX reserves proxy / INR
    elif region == "India":
        if "USD/INR" in yf_df.columns:
            inr = yf_df["USD/INR"].dropna()
            if len(inr) >= 30:
                ret = _pct_change(float(inr.iloc[-1]),
                                  float(inr.iloc[-min(30, len(inr))]))
                if ret > 3:  # INR weakening significantly
                    regime.external_vulnerability = "high"
                    regime.stability_risk = "elevated"
                    regime.notes.append(f"INR weakened {ret:.1f}% over 1m → external pressure")
                elif ret > 1.5:
                    regime.external_vulnerability = "elevated"
                    regime.notes.append(f"INR depreciating {ret:.1f}% over 1m")

    return regime


# ===================================================================
# Cross-regional divergence detection
# ===================================================================

def detect_cross_regional_divergences(
    yf_regions: dict[str, pd.DataFrame],
    fred_regions: dict[str, pd.DataFrame],
    window: int = 7,
) -> list[DivergenceAlert]:
    """Identify divergences across EU, UK, and India."""
    alerts: list[DivergenceAlert] = []

    def _recent_return(df: pd.DataFrame, label: str) -> float | None:
        if label not in df.columns:
            return None
        s = df[label].dropna()
        prior = _get_prior_value(s, window)
        if prior is None:
            return None
        return _pct_change(float(s.iloc[-1]), prior)

    # --- 1. POLICY DIVERGENCE ---
    # Compare equity performance as proxy for policy impact divergence
    eu_eq = _recent_return(yf_regions.get("EU", pd.DataFrame()), "Euro Stoxx 50")
    uk_eq = _recent_return(yf_regions.get("UK", pd.DataFrame()), "FTSE 100")
    in_eq = _recent_return(yf_regions.get("India", pd.DataFrame()), "NIFTY 50")

    if eu_eq is not None and uk_eq is not None:
        if (eu_eq > 2 and uk_eq < -1) or (eu_eq < -1 and uk_eq > 2):
            alerts.append(DivergenceAlert(
                category="growth",
                regions=["EU", "UK"],
                description=f"EU equities ({eu_eq:+.1f}%) and UK equities ({uk_eq:+.1f}%) "
                           f"diverging sharply over {window}d — check relative policy impact",
                severity=2,
            ))

    if eu_eq is not None and in_eq is not None:
        if (eu_eq > 2 and in_eq < -1) or (eu_eq < -1 and in_eq > 2):
            alerts.append(DivergenceAlert(
                category="growth",
                regions=["EU", "India"],
                description=f"EU equities ({eu_eq:+.1f}%) and India equities ({in_eq:+.1f}%) "
                           f"diverging over {window}d — growth differential widening",
                severity=2,
            ))

    if uk_eq is not None and in_eq is not None:
        if (uk_eq > 2 and in_eq < -1) or (uk_eq < -1 and in_eq > 2):
            alerts.append(DivergenceAlert(
                category="growth",
                regions=["UK", "India"],
                description=f"UK equities ({uk_eq:+.1f}%) and India equities ({in_eq:+.1f}%) "
                           f"diverging over {window}d",
                severity=1,
            ))

    # --- 2. CURRENCY IMPLICATIONS ---
    eur_usd = _recent_return(yf_regions.get("EU", pd.DataFrame()), "EUR/USD")
    gbp_usd = _recent_return(yf_regions.get("UK", pd.DataFrame()), "GBP/USD")
    usd_inr = _recent_return(yf_regions.get("India", pd.DataFrame()), "USD/INR")

    if eur_usd is not None and gbp_usd is not None:
        # Both weakening vs USD simultaneously
        if eur_usd < -1.0 and gbp_usd < -1.0:
            alerts.append(DivergenceAlert(
                category="currency",
                regions=["EU", "UK"],
                description=f"EUR ({eur_usd:+.1f}%) and GBP ({gbp_usd:+.1f}%) both weakening "
                           f"vs USD — broad dollar strength or European stress",
                severity=2,
            ))
        # One strengthening while other weakens
        elif (eur_usd > 1.0 and gbp_usd < -1.0) or (eur_usd < -1.0 and gbp_usd > 1.0):
            alerts.append(DivergenceAlert(
                category="currency",
                regions=["EU", "UK"],
                description=f"EUR ({eur_usd:+.1f}%) and GBP ({gbp_usd:+.1f}%) diverging — "
                           f"relative policy or fiscal credibility shift",
                severity=2,
            ))

    if usd_inr is not None and usd_inr > 1.5:
        alerts.append(DivergenceAlert(
            category="currency",
            regions=["India"],
            description=f"INR weakening {usd_inr:+.1f}% vs USD — watch for RBI intervention "
                       f"and capital outflow risk",
            severity=2 if usd_inr > 2.5 else 1,
        ))

    # --- 3. CONTAGION RISKS ---
    # EU sovereign stress → UK gilts spillover
    eu_btp = _recent_return(yf_regions.get("EU", pd.DataFrame()), "Italian BTP ETF")
    uk_gilt = _recent_return(yf_regions.get("UK", pd.DataFrame()), "UK Gilt ETF")

    if eu_btp is not None and uk_gilt is not None:
        if eu_btp < -2.0 and uk_gilt < -1.5:
            alerts.append(DivergenceAlert(
                category="contagion",
                regions=["EU", "UK"],
                description=f"Italian BTPs ({eu_btp:+.1f}%) and UK Gilts ({uk_gilt:+.1f}%) "
                           f"both selling off — sovereign contagion risk",
                severity=2,
            ))

    # Global risk-off → India vulnerability
    global_df = yf_regions.get("Global", pd.DataFrame())
    vix_ret = _recent_return(global_df, "VIX")
    if vix_ret is not None and in_eq is not None:
        if vix_ret > 15 and in_eq < -2:
            alerts.append(DivergenceAlert(
                category="contagion",
                regions=["India", "Global"],
                description=f"VIX spike ({vix_ret:+.1f}%) with NIFTY selloff ({in_eq:+.1f}%) — "
                           f"risk-off capital outflow from India",
                severity=2,
            ))

    # Energy shock asymmetry
    brent = _recent_return(yf_regions.get("EU", pd.DataFrame()), "Brent Crude")
    if brent is not None and abs(brent) > 5:
        direction = "surge" if brent > 0 else "collapse"
        affected = []
        if eu_eq is not None:
            affected.append(f"EU equities {eu_eq:+.1f}%")
        if in_eq is not None:
            affected.append(f"India equities {in_eq:+.1f}%")
        if uk_eq is not None:
            affected.append(f"UK equities {uk_eq:+.1f}%")
        alerts.append(DivergenceAlert(
            category="contagion",
            regions=["EU", "UK", "India"],
            description=f"Oil price {direction} ({brent:+.1f}%) — asymmetric regional impact: "
                       f"{'; '.join(affected)}",
            severity=2,
        ))

    # --- 4. RELATIVE VALUE ---
    # Equity valuations divergence
    returns = {}
    if eu_eq is not None:
        returns["STOXX 600"] = eu_eq
    if uk_eq is not None:
        returns["FTSE 100"] = uk_eq
    if in_eq is not None:
        returns["NIFTY 50"] = in_eq

    if len(returns) >= 2:
        vals = list(returns.values())
        spread = max(vals) - min(vals)
        if spread > 5:
            best = max(returns, key=returns.get)
            worst = min(returns, key=returns.get)
            alerts.append(DivergenceAlert(
                category="relative_value",
                regions=list(returns.keys()),
                description=f"Wide equity performance spread ({spread:.1f}pp over {window}d): "
                           f"{best} outperforming, {worst} underperforming",
                severity=2,
            ))

    alerts.sort(key=lambda a: a.severity, reverse=True)
    return alerts


# ===================================================================
# Forward indicators
# ===================================================================

def build_forward_indicators(
    yf_regions: dict[str, pd.DataFrame],
    regimes: dict[str, RegimeAssessment],
) -> list[str]:
    """Generate forward-looking indicators to watch."""
    indicators: list[str] = []

    for region, regime in regimes.items():
        if regime.growth_stage in ("contraction", "slowdown"):
            indicators.append(
                f"[{region}] Growth weakness — watch for policy pivot signals"
            )
        if regime.inflation_trajectory in ("rising", "peaking"):
            indicators.append(
                f"[{region}] Inflation pressure — monitor next CPI/HICP release for peak confirmation"
            )
        if regime.stability_risk in ("elevated", "high"):
            indicators.append(
                f"[{region}] Financial stability risk {regime.stability_risk} — watch credit spreads and banking sector"
            )
        if regime.external_vulnerability in ("elevated", "high"):
            indicators.append(
                f"[{region}] External vulnerability {regime.external_vulnerability} — monitor FX reserves and capital flows"
            )

    # Standard watches
    indicators.append("[EU] Next ECB meeting and peripheral spread dynamics")
    indicators.append("[UK] BoE MPC voting split and services inflation print")
    indicators.append("[India] RBI forex intervention data and monsoon forecasts")

    return indicators


# ===================================================================
# Cross-regional implications
# ===================================================================

def build_cross_implications(
    regimes: dict[str, RegimeAssessment],
    divergences: list[DivergenceAlert],
) -> list[str]:
    """Synthesize cross-regional investment implications."""
    implications: list[str] = []

    # Policy stance comparison
    stances = {r: reg.policy_stance for r, reg in regimes.items()}
    unique_stances = set(stances.values())
    if len(unique_stances) > 1:
        stance_str = ", ".join(f"{r}: {s}" for r, s in stances.items())
        implications.append(
            f"Policy divergence detected ({stance_str}) — "
            f"creates FX carry trade opportunities and differential rate sensitivity"
        )

    # Growth differential
    growth = {r: reg.growth_stage for r, reg in regimes.items()}
    expanding = [r for r, g in growth.items() if g in ("expansion", "early_recovery")]
    contracting = [r for r, g in growth.items() if g in ("contraction", "slowdown")]
    if expanding and contracting:
        implications.append(
            f"Growth divergence: {', '.join(expanding)} expanding while "
            f"{', '.join(contracting)} slowing — favors relative equity reallocation"
        )

    # Inflation differential
    inflation = {r: reg.inflation_trajectory for r, reg in regimes.items()}
    sticky_regions = [r for r, i in inflation.items() if i in ("sticky", "rising")]
    falling_regions = [r for r, i in inflation.items() if i in ("falling", "bottoming")]
    if sticky_regions and falling_regions:
        implications.append(
            f"Inflation divergence: sticky in {', '.join(sticky_regions)}, "
            f"easing in {', '.join(falling_regions)} — real yield differentials shifting"
        )

    # Contagion alerts
    contagion = [d for d in divergences if d.category == "contagion"]
    if contagion:
        implications.append(
            f"{len(contagion)} contagion risk(s) flagged — cross-border spillover risk elevated"
        )

    if not implications:
        implications.append(
            "Regions broadly aligned — no major cross-regional dislocations detected"
        )

    return implications


# ===================================================================
# Legacy compatibility: analyze_market_data
# ===================================================================

def analyze_market_data(yf_df: pd.DataFrame) -> CrossRegionalResult:
    """Backward-compatible wrapper — scans all data for threshold-exceeding moves."""
    result = CrossRegionalResult(as_of=datetime.utcnow().strftime("%Y-%m-%d"))
    if yf_df.empty:
        return result

    # Run as a single "combined" region analysis
    combined = analyze_region(yf_df, "Global")
    result.regions["Global"] = combined

    # Yield curve spread (US)
    if "US 10Y Yield" in yf_df.columns and "US 2Y Yield" in yf_df.columns:
        y10 = yf_df["US 10Y Yield"].dropna()
        y2 = yf_df["US 2Y Yield"].dropna()
        if not y10.empty and not y2.empty:
            result.yield_curve_us_bps = round(
                (float(y10.iloc[-1]) - float(y2.iloc[-1])) * 100, 1
            )

    return result


# ===================================================================
# Full regional analysis pipeline
# ===================================================================

def run_full_analysis(
    yf_regions: dict[str, pd.DataFrame],
    fred_regions: dict[str, pd.DataFrame],
    yf_combined: pd.DataFrame | None = None,
) -> CrossRegionalResult:
    """Run the complete multi-region analysis pipeline.

    Args:
        yf_regions: {"EU": df, "UK": df, "India": df, "Global": df}
        fred_regions: {"US": df, "EU": df, "UK": df, "India": df}
        yf_combined: All tickers in a single DataFrame (optional)
    """
    result = CrossRegionalResult(as_of=datetime.utcnow().strftime("%Y-%m-%d"))

    # 1. Analyze each region
    for region_key in ["EU", "UK", "India"]:
        yf_df = yf_regions.get(region_key, pd.DataFrame())
        regional = analyze_region(yf_df, region_key)

        # Regime classification
        fred_df = fred_regions.get(region_key, pd.DataFrame())
        regional.regime = classify_regime(yf_df, fred_df, region_key)

        result.regions[region_key] = regional

    # Also analyze global reference
    global_yf = yf_regions.get("Global", pd.DataFrame())
    if not global_yf.empty:
        result.regions["Global"] = analyze_region(global_yf, "Global")

    # 2. US yield curve
    if yf_combined is not None:
        if "US 10Y Yield" in yf_combined.columns and "US 2Y Yield" in yf_combined.columns:
            y10 = yf_combined["US 10Y Yield"].dropna()
            y2 = yf_combined["US 2Y Yield"].dropna()
            if not y10.empty and not y2.empty:
                result.yield_curve_us_bps = round(
                    (float(y10.iloc[-1]) - float(y2.iloc[-1])) * 100, 1
                )

    # 3. Cross-regional divergences
    result.divergence_alerts = detect_cross_regional_divergences(
        yf_regions, fred_regions
    )

    # 4. Forward indicators
    regimes = {k: v.regime for k, v in result.regions.items() if v.regime is not None}
    result.forward_indicators = build_forward_indicators(yf_regions, regimes)

    # 5. Cross-regional implications
    result.cross_implications = build_cross_implications(regimes, result.divergence_alerts)

    return result


# ===================================================================
# Legacy detect_divergences (backward-compatible)
# ===================================================================

def detect_divergences(yf_df: pd.DataFrame, window: int = 7) -> list[str]:
    """Identify notable cross-market divergences over `window` days.

    Retained for backward compatibility with original briefing pipeline.
    """
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

    sp_ret = _recent_return("S&P 500")
    tnx_chg = _recent_return("US 10Y Yield")
    if sp_ret is not None and tnx_chg is not None:
        if sp_ret > 1.5 and tnx_chg < -1.0:
            notes.append("Divergence: equities rallying while yields fall — possible flight-to-quality mixed signal")
        if sp_ret < -1.5 and tnx_chg > 1.0:
            notes.append("Divergence: equities falling while yields rise — possible stagflation concern")

    gold_ret = _recent_return("Gold")
    dxy_ret = _recent_return("DXY")
    if gold_ret is not None and dxy_ret is not None:
        if gold_ret > 2.0 and dxy_ret > 1.0:
            notes.append("Divergence: gold and USD both rising — unusual risk-haven demand")

    cu_ret = _recent_return("Copper")
    if cu_ret is not None and sp_ret is not None:
        if cu_ret < -3.0 and sp_ret > 1.0:
            notes.append("Divergence: copper weak while equities strong — industrial demand may be softening")

    return notes
