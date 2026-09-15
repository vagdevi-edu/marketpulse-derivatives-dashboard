"""
data_provider.py
-----------------
Single source of truth for market data used by the API.

Tries to pull real data via `yfinance` first. If that fails (no internet,
rate-limited, unsupported symbol, or the library isn't installed), it falls
back to a deterministic-but-realistic synthetic generator so the dashboard
always has something sensible to show — useful for demos, dev machines
without internet, and interviews where you don't want a live-data outage
to sink your walkthrough.

Swap point for going fully live:
  - Replace `_mock_price` / `_mock_option_chain` calls with a paid/alt data
    vendor (NSE, Zerodha Kite Connect, Polygon.io, etc.) if yfinance
    coverage isn't enough for Indian derivatives contracts.
"""

import hashlib
import math
import random
from datetime import datetime, timedelta

try:
    import yfinance as yf
    _HAS_YF = True
except ImportError:
    _HAS_YF = False


def _seeded_random(symbol: str) -> random.Random:
    """Deterministic RNG per symbol so mock data is stable across refreshes
    within the same day (nice for demos — numbers don't jump wildly)."""
    seed = int(hashlib.sha256(f"{symbol}-{datetime.now():%Y-%m-%d}".encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed)


def _mock_price(symbol: str) -> dict:
    rnd = _seeded_random(symbol)
    base = 100 + (hash(symbol) % 4000)
    change_pct = rnd.uniform(-2.5, 2.5)
    price = round(base * (1 + change_pct / 100), 2)
    return {
        "symbol": symbol.upper(),
        "price": price,
        "change_pct": round(change_pct, 2),
        "source": "mock",
        "as_of": datetime.utcnow().isoformat(),
    }


def get_price(symbol: str) -> dict:
    if _HAS_YF:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                prev_close = hist["Close"].iloc[-2]
                last = hist["Close"].iloc[-1]
                change_pct = (last - prev_close) / prev_close * 100
                return {
                    "symbol": symbol.upper(),
                    "price": round(float(last), 2),
                    "change_pct": round(float(change_pct), 2),
                    "source": "yfinance",
                    "as_of": datetime.utcnow().isoformat(),
                }
        except Exception:
            pass
    return _mock_price(symbol)


def _mock_option_chain(symbol: str, spot: float) -> dict:
    """Generates a synthetic options chain with a realistic OI 'smile' and
    IV skew so charts look like a real derivatives market snapshot."""
    rnd = _seeded_random(symbol + "-opts")
    strike_step = max(1, round(spot * 0.02 / 5) * 5)
    strikes = [round(spot / strike_step) * strike_step + i * strike_step for i in range(-6, 7)]

    rows = []
    total_call_oi = 0
    total_put_oi = 0
    for k in strikes:
        distance = abs(k - spot) / spot
        # OI peaks near ATM (classic open-interest concentration)
        atm_factor = math.exp(-((distance) ** 2) / 0.004)
        call_oi = int(rnd.uniform(500, 4000) * atm_factor + rnd.uniform(50, 300))
        put_oi = int(rnd.uniform(500, 4000) * atm_factor + rnd.uniform(50, 300))
        # slight put-side skew, common in equity index option chains
        put_oi = int(put_oi * rnd.uniform(1.0, 1.25))
        call_iv = round(18 + distance * 40 + rnd.uniform(-1, 1), 2)
        put_iv = round(19 + distance * 42 + rnd.uniform(-1, 1), 2)

        total_call_oi += call_oi
        total_put_oi += put_oi
        rows.append({
            "strike": k,
            "call_oi": call_oi,
            "call_iv": call_iv,
            "put_oi": put_oi,
            "put_iv": put_iv,
        })

    pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi else None
    return {
        "symbol": symbol.upper(),
        "spot": spot,
        "expiry": (datetime.utcnow() + timedelta(days=(3 - datetime.utcnow().weekday()) % 7 or 7)).strftime("%Y-%m-%d"),
        "rows": rows,
        "put_call_ratio": pcr,
        "source": "mock",
    }


def get_option_chain(symbol: str) -> dict:
    price_info = get_price(symbol)
    spot = price_info["price"]

    if _HAS_YF:
        try:
            ticker = yf.Ticker(symbol)
            expiries = ticker.options
            if expiries:
                chain = ticker.option_chain(expiries[0])
                calls = chain.calls.set_index("strike")
                puts = chain.puts.set_index("strike")
                strikes = sorted(set(calls.index) & set(puts.index))
                # Keep it to a readable window around spot
                strikes = sorted(strikes, key=lambda s: abs(s - spot))[:13]
                strikes.sort()

                rows = []
                total_call_oi = 0
                total_put_oi = 0
                for k in strikes:
                    call_oi = int(calls.loc[k, "openInterest"] or 0)
                    put_oi = int(puts.loc[k, "openInterest"] or 0)
                    call_iv = round(float(calls.loc[k, "impliedVolatility"] or 0) * 100, 2)
                    put_iv = round(float(puts.loc[k, "impliedVolatility"] or 0) * 100, 2)
                    total_call_oi += call_oi
                    total_put_oi += put_oi
                    rows.append({
                        "strike": float(k),
                        "call_oi": call_oi,
                        "call_iv": call_iv,
                        "put_oi": put_oi,
                        "put_iv": put_iv,
                    })

                pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi else None
                return {
                    "symbol": symbol.upper(),
                    "spot": spot,
                    "expiry": expiries[0],
                    "rows": rows,
                    "put_call_ratio": pcr,
                    "source": "yfinance",
                }
        except Exception:
            pass

    return _mock_option_chain(symbol, spot)
