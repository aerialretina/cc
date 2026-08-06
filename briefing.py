"""
Briefing generator – renders the daily EU/UK/India macro monitor as Markdown.

Output format: YYYY-MM-DD_EU_UK_India_monitor.md
Sections:
  1. Executive Summary (3 bullets per region)
  2. Key Changes (24h data with historical context)
  3. Divergence Alerts (when regions moving opposite directions)
  4. Regime Status (traffic light indicators)
  5. Forward Indicators (what to watch next)
  6. Cross-Regional Implications
  7. Regional Data Snapshots
"""

from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
from jinja2 import Template

from analyzer import (
    CrossRegionalResult,
    DivergenceAlert,
    RegimeAssessment,
    Signal,
)
import config

# ===================================================================
# Jinja2 template for the multi-region briefing
# ===================================================================

TEMPLATE = Template("""\
# EU / UK / India Macro Monitor — {{ date }}

> Regional macroeconomic monitoring system: structural shifts and cross-regional divergences.

---

## 1. Executive Summary

{% for region, bullets in executive_summary.items() %}
### {{ region_labels[region] }}
{% for bullet in bullets %}
- {{ bullet }}
{%- endfor %}
{% endfor %}

---

## 2. Key Changes (24h)

{% for region, signals in key_changes.items() %}
### {{ region_labels[region] }}
{% if signals %}
{% for sig in signals %}
{{ loop.index }}. **[{{ sig.severity_label }}]** {{ sig.asset }} ({{ sig.asset_class }}): {{ sig.description }}
{%- endfor %}
{% else %}
*No threshold-exceeding moves detected.*
{% endif %}
{% endfor %}

---

## 3. Divergence Alerts
{% if divergence_alerts %}
{% for alert in divergence_alerts %}
- **[{{ alert.category | upper }}]** ({{ alert.regions | join(', ') }}): {{ alert.description }}
{%- endfor %}
{% else %}
*No significant cross-regional divergences detected.*
{% endif %}

---

## 4. Regime Status

| Dimension | EU | UK | India |
|-----------|----|----|-------|
| Growth Cycle | {{ regime_table.EU.growth }} | {{ regime_table.UK.growth }} | {{ regime_table.India.growth }} |
| Inflation | {{ regime_table.EU.inflation }} | {{ regime_table.UK.inflation }} | {{ regime_table.India.inflation }} |
| Policy Stance | {{ regime_table.EU.policy }} | {{ regime_table.UK.policy }} | {{ regime_table.India.policy }} |
| Stability Risk | {{ regime_table.EU.stability }} | {{ regime_table.UK.stability }} | {{ regime_table.India.stability }} |
| External Vuln. | {{ regime_table.EU.external }} | {{ regime_table.UK.external }} | {{ regime_table.India.external }} |

{% if regime_notes %}
**Regime Notes:**
{% for note in regime_notes %}
- {{ note }}
{%- endfor %}
{% endif %}

---

## 5. Forward Indicators

{% for indicator in forward_indicators %}
- {{ indicator }}
{%- endfor %}

---

## 6. Cross-Regional Implications

{% for impl in cross_implications %}
- {{ impl }}
{%- endfor %}

---

## 7. Regional Data Snapshots

{% for region, table_md in data_tables.items() %}
### {{ region_labels[region] }}

{{ table_md }}

{% endfor %}

{% if yield_curve_bps is not none %}
---

**US Yield Curve (10Y − 2Y):** {{ yield_curve_bps }} bps{{ " — INVERTED" if yield_curve_bps < 0 else "" }}
{% endif %}

---

## Focus Areas

{% for region, areas in focus_areas.items() %}
### {{ region }}
{% for area in areas %}
- {{ area }}
{%- endfor %}
{% endfor %}

---

*Generated {{ timestamp }} UTC | Macro Monitoring System v2.0 — EU/UK/India*
""")


# ===================================================================
# Traffic light emoji mapping
# ===================================================================

TRAFFIC_EMOJI = {
    "green": "🟢",
    "amber": "🟡",
    "red": "🔴",
    "grey": "⚪",
}


def _traffic_label(value: str, regime: RegimeAssessment, dimension: str) -> str:
    """Format a regime dimension with traffic light indicator."""
    color = regime.traffic_light(dimension)
    emoji = TRAFFIC_EMOJI.get(color, "⚪")
    return f"{emoji} {value}"


def _severity_label(severity: int) -> str:
    if severity >= 3:
        return "EXTREME"
    if severity >= 2:
        return "SIGNIFICANT"
    return "NOTABLE"


# ===================================================================
# Builder functions
# ===================================================================

def _build_executive_summary(result: CrossRegionalResult) -> dict[str, list[str]]:
    """3 bullets per region."""
    summary: dict[str, list[str]] = {}
    for region_key in ["EU", "UK", "India"]:
        regional = result.regions.get(region_key)
        if regional and regional.executive_bullets:
            summary[region_key] = regional.executive_bullets[:3]
        else:
            summary[region_key] = ["No significant moves detected."]
    return summary


def _build_key_changes(result: CrossRegionalResult) -> dict[str, list[dict]]:
    """Top signals per region with severity labels."""
    changes: dict[str, list[dict]] = {}
    for region_key in ["EU", "UK", "India"]:
        regional = result.regions.get(region_key)
        if regional and regional.signals:
            changes[region_key] = [
                {
                    "asset": s.asset,
                    "asset_class": s.asset_class,
                    "description": s.description,
                    "severity": s.severity,
                    "severity_label": _severity_label(s.severity),
                    "value": s.value,
                }
                for s in regional.signals[:5]
            ]
        else:
            changes[region_key] = []
    return changes


def _build_divergence_alerts(result: CrossRegionalResult) -> list[dict]:
    """Format divergence alerts for template."""
    return [
        {
            "category": a.category,
            "regions": a.regions,
            "description": a.description,
            "severity": a.severity,
        }
        for a in result.divergence_alerts
    ]


def _build_regime_table(result: CrossRegionalResult) -> dict[str, dict[str, str]]:
    """Build the regime comparison table with traffic lights."""
    table: dict[str, dict[str, str]] = {}
    for region_key in ["EU", "UK", "India"]:
        regional = result.regions.get(region_key)
        if regional and regional.regime:
            r = regional.regime
            table[region_key] = {
                "growth": _traffic_label(r.growth_stage, r, "growth_stage"),
                "inflation": _traffic_label(r.inflation_trajectory, r, "inflation_trajectory"),
                "policy": _traffic_label(r.policy_stance, r, "policy_stance"),
                "stability": _traffic_label(r.stability_risk, r, "stability_risk"),
                "external": _traffic_label(r.external_vulnerability, r, "external_vulnerability"),
            }
        else:
            table[region_key] = {
                "growth": "⚪ n/a",
                "inflation": "⚪ n/a",
                "policy": "⚪ n/a",
                "stability": "⚪ n/a",
                "external": "⚪ n/a",
            }
    return table


def _build_regime_notes(result: CrossRegionalResult) -> list[str]:
    """Collect all regime classification notes."""
    notes: list[str] = []
    for region_key in ["EU", "UK", "India"]:
        regional = result.regions.get(region_key)
        if regional and regional.regime and regional.regime.notes:
            for note in regional.regime.notes:
                notes.append(f"[{region_key}] {note}")
    return notes


def _build_data_tables(result: CrossRegionalResult) -> dict[str, str]:
    """Convert per-region data tables to Markdown strings."""
    tables: dict[str, str] = {}
    for region_key in ["EU", "UK", "India"]:
        regional = result.regions.get(region_key)
        if regional and regional.data_table is not None and not regional.data_table.empty:
            tables[region_key] = regional.data_table.to_markdown(index=False)
        else:
            tables[region_key] = "*No data available.*"
    return tables


# ===================================================================
# Main generation functions
# ===================================================================

def generate_regional_briefing(result: CrossRegionalResult) -> str:
    """Render the full EU/UK/India daily briefing as a Markdown string."""
    region_labels = {
        "EU": config.REGIONS["EU"]["label"],
        "UK": config.REGIONS["UK"]["label"],
        "India": config.REGIONS["India"]["label"],
    }

    md = TEMPLATE.render(
        date=result.as_of,
        timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        region_labels=region_labels,
        executive_summary=_build_executive_summary(result),
        key_changes=_build_key_changes(result),
        divergence_alerts=_build_divergence_alerts(result),
        regime_table=_build_regime_table(result),
        regime_notes=_build_regime_notes(result),
        forward_indicators=result.forward_indicators or ["No specific indicators flagged."],
        cross_implications=result.cross_implications or ["No cross-regional implications detected."],
        data_tables=_build_data_tables(result),
        yield_curve_bps=result.yield_curve_us_bps,
        focus_areas=config.FOCUS_AREAS,
    )
    return md


def save_regional_briefing(md: str, output_dir: str | None = None) -> str:
    """Write the regional briefing to a dated Markdown file."""
    output_dir = output_dir or os.getenv("OUTPUT_DIR", "./output")
    os.makedirs(output_dir, exist_ok=True)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    path = os.path.join(output_dir, f"{today}_EU_UK_India_monitor.md")

    with open(path, "w") as f:
        f.write(md)

    return path


# ===================================================================
# Legacy compatibility (original single-region briefing)
# ===================================================================

_LEGACY_TEMPLATE = Template("""\
# Macro Daily Brief — {{ date }}

## Summary

{{ summary }}

---

## Key Developments
{% for sig in top_signals %}
{{ loop.index }}. **{{ sig.asset }}** ({{ sig.asset_class }}): {{ sig.description }}
{%- endfor %}
{% if divergences %}

### Cross-Market Divergences
{% for d in divergences %}
- {{ d }}
{%- endfor %}
{% endif %}

---

## Data Snapshot

{{ data_table }}

{% if yield_curve_bps is not none %}
**Yield curve (10Y − 2Y):** {{ yield_curve_bps }} bps{{ " — INVERTED" if yield_curve_bps < 0 else "" }}
{% endif %}

---

## Analysis

{{ analysis }}

---

## Watch List

{{ watchlist }}
""")


def _build_summary(signals: list[Signal], divergences: list[str],
                    yield_curve_bps: float | None) -> str:
    if not signals:
        return "Markets were broadly quiet with no indicators exceeding significance thresholds."

    top = signals[:3]
    parts: list[str] = []
    for s in top:
        direction = "higher" if s.value > 0 else "lower"
        parts.append(f"{s.asset} moved sharply {direction}")

    summary = "Today's most notable moves: " + "; ".join(parts) + "."

    if yield_curve_bps is not None and yield_curve_bps < 0:
        summary += f" The yield curve remains inverted at {yield_curve_bps} bps, signaling continued recession risk."

    if divergences:
        summary += f" {len(divergences)} cross-market divergence(s) detected — see below."

    return summary


def _build_analysis(signals: list[Signal], divergences: list[str]) -> str:
    lines: list[str] = []
    by_class: dict[str, list[Signal]] = {}
    for s in signals:
        by_class.setdefault(s.asset_class, []).append(s)

    if "rates" in by_class:
        rate_sigs = by_class["rates"]
        avg = sum(s.value for s in rate_sigs) / len(rate_sigs)
        direction = "rising" if avg > 0 else "falling"
        lines.append(
            f"**Rates:** Yields are {direction} on average across flagged tenors, "
            f"suggesting shifting expectations for monetary policy tightening."
        )

    if "equities" in by_class:
        eq_sigs = by_class["equities"]
        avg = sum(s.value for s in eq_sigs) / len(eq_sigs)
        tone = "risk-on" if avg > 0 else "risk-off"
        lines.append(
            f"**Equities:** Broad {tone} tone across major indices. "
            f"Monitor for follow-through or mean-reversion in coming sessions."
        )

    if "commodities" in by_class:
        lines.append(
            "**Commodities:** Notable commodity price action may reflect shifts in "
            "global demand expectations or supply-side disruptions."
        )

    if "currencies" in by_class:
        lines.append(
            "**FX:** Significant currency moves may indicate diverging central bank "
            "policy expectations or capital flow rebalancing."
        )

    if divergences:
        lines.append(
            "**Divergences:** The detected cross-market divergences warrant close "
            "monitoring — they may indicate a regime transition or dislocation."
        )

    if not lines:
        lines.append("No threshold-exceeding moves detected. Markets are in a low-volatility regime.")

    return "\n\n".join(lines)


def _build_watchlist(signals: list[Signal], yield_curve_bps: float | None) -> str:
    items: list[str] = []

    severe = [s for s in signals if s.severity >= 2]
    if severe:
        items.append("- Continue monitoring " + ", ".join(s.asset for s in severe[:5]) +
                      " for follow-through or reversal.")

    if yield_curve_bps is not None:
        if yield_curve_bps < 0:
            items.append("- Yield curve inversion persists — watch for labor-market softening "
                         "and credit-spread widening.")
        elif yield_curve_bps < 30:
            items.append("- Yield curve is flat — a further flattening or inversion could "
                         "signal recession expectations.")

    items.append("- Upcoming central bank meetings and economic data releases may catalyze the next move.")

    return "\n".join(items) if items else "- No specific items flagged."


def _df_to_markdown(df: pd.DataFrame | None) -> str:
    if df is None or df.empty:
        return "*No data available.*"
    return df.to_markdown(index=False)


def generate_briefing(result: CrossRegionalResult,
                      divergences: list[str] | None = None) -> str:
    """Legacy single-briefing format for backward compatibility."""
    divergences = divergences or []

    # Collect all signals across regions
    all_signals = []
    for regional in result.regions.values():
        all_signals.extend(regional.signals)
    all_signals.sort(key=lambda s: s.severity, reverse=True)
    top_signals = all_signals[:5]

    # Collect all data tables
    all_tables = []
    for regional in result.regions.values():
        if regional.data_table is not None:
            all_tables.append(regional.data_table)
    combined_table = pd.concat(all_tables) if all_tables else None

    md = _LEGACY_TEMPLATE.render(
        date=result.as_of,
        summary=_build_summary(all_signals, divergences, result.yield_curve_us_bps),
        top_signals=top_signals,
        divergences=divergences,
        data_table=_df_to_markdown(combined_table),
        yield_curve_bps=result.yield_curve_us_bps,
        analysis=_build_analysis(all_signals, divergences),
        watchlist=_build_watchlist(all_signals, result.yield_curve_us_bps),
    )
    return md


def save_briefing(md: str, output_dir: str | None = None) -> str:
    """Write the briefing to a dated Markdown file. Returns the file path."""
    output_dir = output_dir or os.getenv("OUTPUT_DIR", "./output")
    os.makedirs(output_dir, exist_ok=True)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    path = os.path.join(output_dir, f"{today}_macro_brief.md")

    with open(path, "w") as f:
        f.write(md)

    return path
