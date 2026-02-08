#!/usr/bin/env python3
"""
Macro Monitoring Assistant — daily runner.

Regional focus: EU (Eurozone), UK, India
Detects structural shifts and cross-regional divergences.

Usage:
    python run.py                  # run regional monitor once
    python run.py --schedule       # run on a daily schedule (06:30 UTC)
    python run.py --legacy         # run original single-briefing format
"""

import argparse
import logging
import sys

import schedule
import time

from data_fetcher import fetch_all, fetch_all_regional
from analyzer import (
    analyze_market_data,
    detect_divergences,
    run_full_analysis,
)
from briefing import (
    generate_briefing,
    save_briefing,
    generate_regional_briefing,
    save_regional_briefing,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("macro-monitor")


def regional_run() -> None:
    """Execute the EU/UK/India regional macro monitoring cycle."""
    log.info("=== Starting EU/UK/India regional macro monitoring run ===")

    # 1. Fetch all regional data
    data = fetch_all_regional()
    fred_data = data["fred"]
    yf_data = data["yf"]
    yf_combined = data["yf_combined"]

    total_yf = sum(len(df.columns) for df in yf_data.values() if not df.empty)
    total_fred = sum(len(df.columns) for df in fred_data.values() if not df.empty)
    log.info("Fetched %d YF series across regions, %d FRED series across regions",
             total_yf, total_fred)

    if all(df.empty for df in yf_data.values()):
        log.error("No Yahoo Finance data returned for any region — aborting run.")
        return

    # 2. Run full regional analysis
    result = run_full_analysis(yf_data, fred_data, yf_combined)

    total_signals = sum(len(r.signals) for r in result.regions.values())
    log.info("Detected %d signals across regions, %d divergence alerts",
             total_signals, len(result.divergence_alerts))

    for region_key in ["EU", "UK", "India"]:
        regional = result.regions.get(region_key)
        if regional:
            regime = regional.regime
            if regime:
                log.info("[%s] Growth: %s | Inflation: %s | Policy: %s | Stability: %s",
                         region_key, regime.growth_stage, regime.inflation_trajectory,
                         regime.policy_stance, regime.stability_risk)

    # 3. Generate and save regional briefing
    md = generate_regional_briefing(result)
    path = save_regional_briefing(md)

    log.info("Regional briefing saved to %s", path)
    print(f"\n{'=' * 70}")
    print(md)
    print(f"{'=' * 70}")
    print(f"Regional briefing written to: {path}")


def legacy_run() -> None:
    """Execute the original single-briefing macro monitoring cycle."""
    log.info("=== Starting legacy macro monitoring run ===")

    # 1. Fetch data
    data = fetch_all()
    yf_df = data["yf"]
    fred_df = data["fred"]

    if yf_df.empty:
        log.error("No Yahoo Finance data returned — aborting run.")
        return

    log.info("Fetched %d market series, %d FRED series",
             len(yf_df.columns), len(fred_df.columns))

    # 2. Analyze
    result = analyze_market_data(yf_df)
    divergences = detect_divergences(yf_df)

    total_signals = sum(len(r.signals) for r in result.regions.values())
    log.info("Detected %d signals, %d divergences",
             total_signals, len(divergences))

    # 3. Generate and save briefing
    md = generate_briefing(result, divergences)
    path = save_briefing(md)

    log.info("Briefing saved to %s", path)
    print(f"\n{'=' * 60}")
    print(md)
    print(f"{'=' * 60}")
    print(f"Briefing written to: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Macro Monitoring Assistant — EU/UK/India Regional Monitor"
    )
    parser.add_argument("--schedule", action="store_true",
                        help="Run on a daily schedule at 06:30 UTC")
    parser.add_argument("--legacy", action="store_true",
                        help="Use original single-briefing format instead of regional")
    args = parser.parse_args()

    run_fn = legacy_run if args.legacy else regional_run

    if args.schedule:
        log.info("Scheduling daily run at 06:30 UTC (mode: %s)",
                 "legacy" if args.legacy else "regional")
        schedule.every().day.at("06:30").do(run_fn)
        # Also run immediately on startup
        run_fn()
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        run_fn()


if __name__ == "__main__":
    main()
