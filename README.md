# Macro Monitoring Assistant

A daily macroeconomic monitoring tool that identifies significant shifts in the global economy.

## What it does

- Fetches market data from Yahoo Finance and FRED (Federal Reserve Economic Data)
- Detects threshold-exceeding moves in equities, rates, currencies, and commodities
- Identifies cross-market divergences (e.g., stocks up + yields down)
- Generates a concise daily briefing in Markdown format

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your FRED API key (free at https://fred.stlouisfed.org/docs/api/api_key.html)
```

## Usage

```bash
# Run once — generates today's briefing in ./output/
python run.py

# Run on a daily schedule (06:30 UTC)
python run.py --schedule
```

## Output

Each run produces a file like `output/2026-02-08_macro_brief.md` containing:

- **Summary** — top-line overview
- **Key Developments** — threshold-exceeding moves ranked by severity
- **Data Snapshot** — table of current prices and changes (1d, 1w, 1m)
- **Analysis** — causal interpretation grouped by asset class
- **Watch List** — items to monitor going forward

## Configuration

Edit `config.py` to adjust:

- FRED series IDs and Yahoo Finance tickers
- Significance thresholds (bps for yields, % for everything else)
- Lookback windows for comparison periods
- Asset class groupings

## Data Sources

| Source | Coverage | Auth |
|--------|----------|------|
| Yahoo Finance (via `yfinance`) | Equities, FX, commodities, bond yields | None |
| FRED (via `fredapi`) | Treasury yields, CPI, GDP, unemployment, etc. | Free API key |
