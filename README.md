# MarketPulse — Equity & Derivatives Dashboard

A weekend-scope full-stack project: a watchlist-driven dashboard that shows
live-ish equity prices and an options chain with open interest (OI),
implied volatility (IV), and a computed **Put-Call Ratio (PCR)** — the
standard sentiment indicator used in derivatives markets (PCR > 1 skews
bearish/hedging, PCR < 1 skews bullish).

## Why this project

Built specifically to demonstrate genuine interest in derivatives markets
for trainee/analyst hiring (e.g. Futures First's Trainee – International
Markets role) — not just backend engineering ability. The PCR calculation
and OI-by-strike visualization are the parts that actually show market
domain understanding, not just API-wiring skill.

## Stack

- **Backend**: FastAPI + SQLite (watchlist persistence)
- **Data**: `yfinance` when internet/API access is available, with a
  deterministic synthetic data generator as a graceful fallback — the
  dashboard always renders something realistic, live feed or not
- **Frontend**: single-file HTML/JS + Chart.js (no build step required)

## Run it

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Then open `frontend/index.html` in a browser (it talks to
`http://localhost:8000/api`).

## What it does

- Maintains a watchlist (add/remove symbols), persisted in SQLite
- Shows current price + % change per symbol
- Pulls the nearest-expiry options chain for a symbol and computes:
  - Open interest per strike (calls vs puts)
  - Implied volatility per strike
  - Put-Call Ratio (aggregate put OI ÷ call OI)
- Renders an OI-by-strike bar chart to visually spot where the market is
  positioned (OI concentration = where big money expects price to pin or
  resist)

## Talking points for an interview

- **Why PCR**: it's a real, widely-used derivatives sentiment metric —
  including it (not just "showing a chart") signals you understand what
  the numbers mean, not just how to fetch them.
- **Graceful degradation**: the mock-data fallback means the demo never
  breaks mid-interview if wifi drops or a data vendor rate-limits you —
  worth mentioning as a deliberate reliability choice, not a shortcut.
- **Extending it**: natural next steps to mention if asked — historical
  OI build-up over the session (not just a snapshot), max pain
  calculation, or swapping the data source to NSE/Zerodha Kite Connect
  for real Indian index options coverage.

## Suggested resume bullet

**MarketPulse — Equity & Derivatives Dashboard** — Python, FastAPI, SQLite, Chart.js

- Built a full-stack dashboard computing options-chain analytics (open
  interest, implied volatility, Put-Call Ratio) across strikes for a
  watchlist of equities and indices, with a resilient live/synthetic data
  layer to guarantee uptime for demos.
