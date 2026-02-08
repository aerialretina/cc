"""
Briefing generator – renders the daily macro brief as Markdown.
"""

from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
from jinja2 import Template

from analyzer import AnalysisResult, Signal

TEMPLATE = Template("""\
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
    """Auto-generate a 2-3 sentence summary from the signals."""
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
    """Generate a brief causal / implications paragraph."""
    lines: list[str] = []

    # Group signals by asset class
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


def generate_briefing(result: AnalysisResult,
                      divergences: list[str] | None = None) -> str:
    """Render the full daily briefing as a Markdown string."""
    divergences = divergences or []
    top_signals = result.signals[:5]

    md = TEMPLATE.render(
        date=result.as_of,
        summary=_build_summary(result.signals, divergences, result.yield_curve_bps),
        top_signals=top_signals,
        divergences=divergences,
        data_table=_df_to_markdown(result.data_table),
        yield_curve_bps=result.yield_curve_bps,
        analysis=_build_analysis(result.signals, divergences),
        watchlist=_build_watchlist(result.signals, result.yield_curve_bps),
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
