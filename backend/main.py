"""
main.py — MarketPulse API

A small FastAPI service backing a stock/derivatives dashboard:
  - live-ish price quotes
  - options chain with per-strike OI/IV and a computed Put-Call Ratio (PCR)
  - a persisted watchlist (SQLite)

Run:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from data_provider import get_price, get_option_chain

DB_PATH = Path(__file__).parent / "watchlist.db"

app = FastAPI(title="MarketPulse API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before deploying anywhere real
    allow_methods=["*"],
    allow_headers=["*"],
)


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS watchlist (
                symbol TEXT PRIMARY KEY,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        # A sensible default watchlist so the dashboard isn't empty on first run
        for sym in ("^NSEI", "^NSEBANK", "RELIANCE.NS", "AAPL"):
            conn.execute("INSERT OR IGNORE INTO watchlist (symbol) VALUES (?)", (sym,))


init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/price/{symbol}")
def price(symbol: str):
    return get_price(symbol)


@app.get("/api/options/{symbol}")
def options(symbol: str):
    return get_option_chain(symbol)


@app.get("/api/watchlist")
def list_watchlist():
    with get_db() as conn:
        rows = conn.execute("SELECT symbol FROM watchlist ORDER BY added_at").fetchall()
    symbols = [r["symbol"] for r in rows]
    return {"symbols": symbols, "quotes": [get_price(s) for s in symbols]}


@app.post("/api/watchlist/{symbol}")
def add_to_watchlist(symbol: str):
    symbol = symbol.upper().strip()
    if not symbol:
        raise HTTPException(400, "Symbol required")
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO watchlist (symbol) VALUES (?)", (symbol,))
    return {"added": symbol}


@app.delete("/api/watchlist/{symbol}")
def remove_from_watchlist(symbol: str):
    with get_db() as conn:
        conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol.upper(),))
    return {"removed": symbol.upper()}
