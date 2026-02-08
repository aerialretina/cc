# Macro Monitoring Assistant — EU / UK / India

A daily macroeconomic monitoring system focused on EU (Eurozone), UK, and India markets. Detects structural shifts and cross-regional divergences.

## What it does

- Fetches market data from Yahoo Finance and FRED for three regions + global reference
- Analyzes each region independently: equities, bonds, currencies, commodities
- Detects cross-regional divergences (growth, currency, contagion, relative value)
- Classifies macro regime per region (growth cycle, inflation, policy, stability, external risk)
- Flags extreme moves (>2 standard deviations) and threshold-exceeding changes
- Generates a structured daily briefing in Markdown format

## Regions & Coverage

| Region | Equities | Bonds/Rates | Currencies | Key Focus |
|--------|----------|-------------|------------|-----------|
| EU | STOXX 600, DAX, CAC 40, FTSE MIB, IBEX 35, STOXX Banks | Bund/BTP ETFs, ECB rate | EUR/USD, EUR/GBP, EUR/CHF | Peripheral spreads, ECB policy, energy |
| UK | FTSE 100, FTSE 250 | Gilt ETFs (nominal, short, IL) | GBP/USD, GBP/EUR | Stagflation risk, gilt stability, services inflation |
| India | NIFTY 50, NIFTY Bank, Sensex, NIFTY IT | RBI rate (FRED) | USD/INR, EUR/INR | Oil sensitivity, monsoon, FDI flows |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your FRED API key (free at https://fred.stlouisfed.org/docs/api/api_key.html)
```

## Usage

```bash
# Run regional monitor (EU/UK/India) — default mode
python run.py

# Run on a daily schedule (06:30 UTC)
python run.py --schedule

# Run legacy single-briefing format
python run.py --legacy
```

## Output

Each run produces `output/YYYY-MM-DD_EU_UK_India_monitor.md` containing:

1. **Executive Summary** — 3 bullets per region
2. **Key Changes** — 24h data with severity classification
3. **Divergence Alerts** — cross-regional divergences (growth, currency, contagion, relative value)
4. **Regime Status** — traffic light table (growth, inflation, policy, stability, external vulnerability)
5. **Forward Indicators** — what to watch next
6. **Cross-Regional Implications** — investment implications from divergences
7. **Regional Data Snapshots** — full data tables per region with 1d/1w/1m changes and z-scores

## Configuration

Edit `config.py` to adjust:

- Regional FRED series and Yahoo Finance tickers
- Significance thresholds (bps for yields, % for equities/FX/commodities)
- Lookback windows for comparison periods
- Asset class groupings per region
- Regime classification parameters and traffic light mappings
- Focus areas per region

## Data Sources

| Source | Coverage | Auth |
|--------|----------|------|
| Yahoo Finance (`yfinance`) | Equities, FX, commodities, bond ETFs | None |
| FRED (`fredapi`) | CPI/HICP, policy rates, 10Y yields, unemployment, PPI, M3 | Free API key |

## Architecture

```
config.py          — Regional tickers, FRED series, thresholds, regime config
data_fetcher.py    — FRED + YF fetchers with per-region and combined modes
analyzer.py        — Signal detection, regime classification, cross-regional divergences
briefing.py        — Jinja2 template rendering for regional and legacy formats
run.py             — CLI entry point with scheduling support
```
