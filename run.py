#!/usr/bin/env python3
"""
Macro Monitoring Assistant — daily runner.

Usage:
    python run.py              # run once and generate today's briefing
    python run.py --schedule   # run on a daily schedule (06:30 UTC)
"""

import argparse
import logging
import sys

import schedule
import time

from data_fetcher import fetch_all
from analyzer import analyze_market_data, detect_divergences
from briefing import generate_briefing, save_briefing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("macro-monitor")


def daily_run() -> None:
    """Execute a single daily macro monitoring cycle."""
    log.info("=== Starting daily macro monitoring run ===")

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

    log.info("Detected %d signals, %d divergences",
             len(result.signals), len(divergences))

    # 3. Generate and save briefing
    md = generate_briefing(result, divergences)
    path = save_briefing(md)

    log.info("Briefing saved to %s", path)
    print(f"\n{'=' * 60}")
    print(md)
    print(f"{'=' * 60}")
    print(f"Briefing written to: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Macro Monitoring Assistant")
    parser.add_argument("--schedule", action="store_true",
                        help="Run on a daily schedule at 06:30 UTC")
    args = parser.parse_args()

    if args.schedule:
        log.info("Scheduling daily run at 06:30 UTC")
        schedule.every().day.at("06:30").do(daily_run)
        # Also run immediately on startup
        daily_run()
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        daily_run()


if __name__ == "__main__":
    main()
