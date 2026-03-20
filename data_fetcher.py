"""
Data Fetcher — Yahoo Finance v8/finance/chart API
Mirrors app/api/stocks/route.ts with Streamlit caching.
All fetch calls use a single chart endpoint (no redundant quote call).
"""

import time
import requests
import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from nifty_indices import NIFTY_INDICES, SECTORS, get_all_stocks, get_sector_for_symbol
from technical_indicators import (
    calculate_rsi, calculate_ema, calculate_sma,
    calculate_dma_status, calculate_momentum_score,
    detect_nr7, detect_nr4, detect_vcp, detect_pocket_pivot, detect_rs_divergence,
    calculate_relative_strength, calculate_rrg_values, get_rrg_quadrant,
    calculate_volume_ratio, assign_grade,
)

YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
HEADERS    = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


# ── Low-level fetch ────────────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def fetch_chart(symbol: str, range_: str = "6mo", interval: str = "1d") -> dict:
    """
    Fetch OHLCV + meta from Yahoo Finance v8 chart endpoint.
    Returns {"ohlcv": [...], "meta": {...}} or {"ohlcv": [], "meta": None}.
    Cached for 60 seconds via st.cache_data.
    """
    url = f"{YAHOO_BASE}/{requests.utils.quote(symbol)}?range={range_}&interval={interval}&includePrePost=false"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data   = resp.json()
        result = data.get("chart", {}).get("result", [None])[0]
        if not result:
            return {"ohlcv": [], "meta": None}

        m = result.get("meta", {})
        meta = {
            "symbol":                   m.get("symbol", symbol),
            "short_name":               m.get("shortName", symbol),
            "price":                    m.get("regularMarketPrice", 0.0),
            "prev_close":               m.get("previousClose") or m.get("chartPreviousClose", 0.0),
            "volume":                   m.get("regularMarketVolume", 0),
            "day_high":                 m.get("regularMarketDayHigh", 0.0),
            "day_low":                  m.get("regularMarketDayLow", 0.0),
            "week52_high":              m.get("fiftyTwoWeekHigh", 0.0),
            "week52_low":               m.get("fiftyTwoWeekLow", 0.0),
            "avg_volume_3m":            m.get("averageDailyVolume3Month", 0),
        }

        ohlcv = []
        ts    = result.get("timestamp", [])
        q     = (result.get("indicators", {}).get("quote") or [{}])[0]
        for i, t in enumerate(ts):
            c = (q.get("close") or [])[i] if i < len(q.get("close") or []) else None
            o = (q.get("open")  or [])[i] if i < len(q.get("open")  or []) else None
            if c is not None and o is not None:
                ohlcv.append({
                    "date":   str(time.strftime("%Y-%m-%d", time.gmtime(t))),
                    "open":   o or 0.0,
                    "high":   (q.get("high",   [0.0])[i] or 0.0),
                    "low":    (q.get("low",    [0.0])[i] or 0.0),
                    "close":  c or 0.0,
                    "volume": (q.get("volume", [0])[i]   or 0),
                })

        return {"ohlcv": ohlcv, "meta": meta}

    except Exception as e:
        st.warning(f"⚠ Fetch error {symbol}: {e}", icon="⚠️")
        return {"ohlcv": [], "meta": None}


# ── Process one stock ──────────────────────────────────────────────────────────

def process_stock(symbol: str, bench_ohlcv: list, sector_name: str = "Unknown") -> Optional[dict]:
    """Compute all TA signals for a single stock. Returns None if data insufficient."""
    res  = fetch_chart(symbol, "6mo", "1d")
    ohlcv = res["ohlcv"]
    meta  = res["meta"]

    if len(ohlcv) < 20 or not meta:
        return None

    closes  = [d["close"]  for d in ohlcv]
    volumes = [d["volume"] for d in ohlcv]

    rsi_vals  = calculate_rsi(closes)
    ema5      = calculate_ema(closes, 5)
    ema10     = calculate_ema(closes, 10)
    ema21     = calculate_ema(closes, 21)
    ema50     = calculate_ema(closes, 50)
    dma       = calculate_dma_status(closes)
    nr7       = detect_nr7(ohlcv)
    nr4       = detect_nr4(ohlcv)
    vcp       = detect_vcp(ohlcv)
    pp        = detect_pocket_pivot(ohlcv)
    rs_div    = detect_rs_divergence(ohlcv, bench_ohlcv) if len(bench_ohlcv) >= 20 else [False] * len(ohlcv)
    mom       = calculate_momentum_score(ohlcv)
    vol_ratio = calculate_volume_ratio(volumes)

    bench_closes = [d["close"] for d in bench_ohlcv]
    rs     = calculate_relative_strength(closes, bench_closes)
    rrg    = calculate_rrg_values(closes, bench_closes)
    quad   = get_rrg_quadrant(rrg["rs_ratio"], rrg["rs_momentum"])

    price     = meta["price"]
    prev      = meta["prev_close"]
    change    = price - prev
    chg_pct   = (change / prev * 100) if prev else 0.0

    return {
        "symbol":        symbol,
        "name":          meta["short_name"],
        "sector":        sector_name,
        "price":         price,
        "change":        change,
        "change_pct":    chg_pct,
        "volume":        meta["volume"],
        "avg_volume":    meta["avg_volume_3m"],
        "high52w":       meta["week52_high"],
        "low52w":        meta["week52_low"],
        "rsi":           rsi_vals[-1],
        "ema5":          ema5[-1],
        "ema10":         ema10[-1],
        "ema21":         ema21[-1],
        "ema50":         ema50[-1],
        "dma20":         dma["dma20"],
        "dma50":         dma["dma50"],
        "dma200":        dma["dma200"],
        "above20dma":    dma["above20"],
        "above50dma":    dma["above50"],
        "above200dma":   dma["above200"],
        "is_nr7":        nr7[-1],
        "is_nr4":        nr4[-1],
        "is_vcp":        vcp[-1],
        "is_pocket_pivot": pp[-1],
        "is_rs_div":     rs_div[-1] if rs_div else False,
        "momentum":      mom,
        "vol_ratio":     vol_ratio,
        "rs":            rs,
        "rs_ratio":      rrg["rs_ratio"],
        "rs_momentum":   rrg["rs_momentum"],
        "rrg_quadrant":  quad,
        "ohlcv":         ohlcv[-60:],   # last 60 bars for chart
    }


# ── Sector helpers ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def fetch_sector_data(sector_name: str) -> Optional[dict]:
    """Full sector drill-down: all stocks + sector-level aggregates."""
    sector = next((s for s in SECTORS if s["name"] == sector_name), None)
    if not sector:
        return None

    bench = fetch_chart("^NSEI", "6mo", "1d")["ohlcv"]

    stocks = []
    for s in sector["stocks"]:
        result = process_stock(s["symbol"], bench, sector_name)
        if result:
            stocks.append(result)

    if not stocks:
        return None

    avg_chg  = sum(s["change_pct"] for s in stocks) / len(stocks)
    avg_rsi  = sum(s["rsi"] for s in stocks if s["rsi"] == s["rsi"]) / max(1, sum(1 for s in stocks if s["rsi"] == s["rsi"]))
    avg_mom  = sum(s["momentum"] for s in stocks) / len(stocks)
    breadth  = sum(1 for s in stocks if s["above20dma"]) / len(stocks) * 100
    avg_volr = sum(s["vol_ratio"] for s in stocks) / len(stocks)

    sec_hist = fetch_chart(sector["index_symbol"], "6mo", "1d")["ohlcv"]
    bench_closes = [d["close"] for d in bench]
    if sec_hist:
        rrg  = calculate_rrg_values([d["close"] for d in sec_hist], bench_closes)
    else:
        rrg  = {"rs_ratio": 100.0, "rs_momentum": 100.0}

    sorted_stocks = sorted(stocks, key=lambda s: s["change_pct"], reverse=True)
    industries    = list(dict.fromkeys(s["industry"] for s in sector["stocks"]))

    return {
        "name":         sector["name"],
        "color":        sector["color"],
        "change":       avg_chg,
        "rsi":          avg_rsi,
        "momentum":     avg_mom,
        "breadth":      breadth,
        "vol_ratio":    avg_volr,
        "rs_ratio":     rrg["rs_ratio"],
        "rs_momentum":  rrg["rs_momentum"],
        "rrg_quadrant": get_rrg_quadrant(rrg["rs_ratio"], rrg["rs_momentum"]),
        "stocks":       stocks,
        "top_gainers":  sorted_stocks[:3],
        "top_losers":   sorted_stocks[-3:][::-1],
        "industries":   industries,
    }


@st.cache_data(ttl=60, show_spinner=False)
def fetch_all_sectors() -> list:
    """All-sectors overview with parallel fetching."""
    bench = fetch_chart("^NSEI", "6mo", "1d")["ohlcv"]
    bench_closes = [d["close"] for d in bench]

    results = []

    def _process_sector(sector: dict) -> dict:
        stocks = []
        for s in sector["stocks"]:
            r = process_stock(s["symbol"], bench, sector["name"])
            if r:
                stocks.append(r)

        if not stocks:
            return {
                "name": sector["name"], "color": sector["color"],
                "index_symbol": sector["index_symbol"],
                "change": 0, "rsi": 50, "momentum": 50,
                "breadth": 0, "vol_ratio": 1,
                "rs_ratio": 100, "rs_momentum": 100,
                "rrg_quadrant": "Lagging",
                "top_gainers": [], "top_losers": [],
                "stock_count": len(sector["stocks"]),
            }

        avg_chg  = sum(s["change_pct"] for s in stocks) / len(stocks)
        avg_rsi  = sum(s["rsi"] for s in stocks if s["rsi"] == s["rsi"]) / max(1, sum(1 for s in stocks if s["rsi"] == s["rsi"]))
        avg_mom  = sum(s["momentum"] for s in stocks) / len(stocks)
        breadth  = sum(1 for s in stocks if s["above20dma"]) / len(stocks) * 100
        avg_volr = sum(s["vol_ratio"] for s in stocks) / len(stocks)

        sec_hist = fetch_chart(sector["index_symbol"], "6mo", "1d")["ohlcv"]
        rrg = calculate_rrg_values([d["close"] for d in sec_hist], bench_closes) if sec_hist else {"rs_ratio": 100.0, "rs_momentum": 100.0}

        sorted_s = sorted(stocks, key=lambda s: s["change_pct"], reverse=True)
        return {
            "name": sector["name"], "color": sector["color"],
            "index_symbol": sector["index_symbol"],
            "change": avg_chg, "rsi": avg_rsi, "momentum": avg_mom,
            "breadth": breadth, "vol_ratio": avg_volr,
            "rs_ratio": rrg["rs_ratio"], "rs_momentum": rrg["rs_momentum"],
            "rrg_quadrant": get_rrg_quadrant(rrg["rs_ratio"], rrg["rs_momentum"]),
            "top_gainers": sorted_s[:3],
            "top_losers":  sorted_s[-3:][::-1],
            "stock_count": len(sector["stocks"]),
        }

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_process_sector, s): s for s in SECTORS}
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as e:
                st.warning(f"Sector error: {e}")

    # Sort back to original SECTOR order
    order = {s["name"]: i for i, s in enumerate(SECTORS)}
    return sorted(results, key=lambda r: order.get(r["name"], 99))


@st.cache_data(ttl=60, show_spinner=False)
def fetch_indices() -> list:
    """Fetch all NIFTY_INDICES with RSI."""
    results = []
    for name, symbol in NIFTY_INDICES.items():
        res   = fetch_chart(symbol, "3mo", "1d")
        ohlcv = res["ohlcv"]
        meta  = res["meta"]
        if not meta:
            continue
        closes  = [d["close"] for d in ohlcv]
        rsi_arr = calculate_rsi(closes)
        results.append({
            "name":        name,
            "symbol":      symbol,
            "price":       meta["price"],
            "change":      meta["price"] - meta["prev_close"],
            "change_pct":  (meta["price"] - meta["prev_close"]) / meta["prev_close"] * 100 if meta["prev_close"] else 0,
            "rsi":         rsi_arr[-1] if rsi_arr else float("nan"),
            "volume":      meta["volume"],
        })
    return results


@st.cache_data(ttl=60, show_spinner=False)
def fetch_screener(
    rsi_min: float = 0, rsi_max: float = 100,
    momentum_min: float = 0,
    volume_breakout: bool = False,
    pattern: str = "all",
    rrg_quadrant: str = "all",
    dma_filter: str = "all",
) -> list:
    """Screen full universe with filters."""
    bench = fetch_chart("^NSEI", "6mo", "1d")["ohlcv"]

    # Compute real sector momentum for grading
    sector_mom_map = {}
    for sec in SECTORS:
        sh = fetch_chart(sec["index_symbol"], "3mo", "1d")["ohlcv"]
        if len(sh) >= 20:
            closes = [d["close"] for d in sh]
            chg = (closes[-1] - closes[-20]) / closes[-20]
            sector_mom_map[sec["name"]] = 50 + chg * 100
        else:
            sector_mom_map[sec["name"]] = 50.0

    all_stocks = get_all_stocks()

    def _proc(s):
        return process_stock(s["symbol"], bench, s["sector"])

    stocks = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_proc, s): s for s in all_stocks}
        for fut in as_completed(futures):
            try:
                r = fut.result()
                if r:
                    stocks.append(r)
            except Exception:
                pass

    # Apply filters
    filtered = []
    for s in stocks:
        rsi_ok  = rsi_min <= (s["rsi"] or 0) <= rsi_max
        mom_ok  = s["momentum"] >= momentum_min
        vol_ok  = not volume_breakout or s["vol_ratio"] > 1.5
        pat_ok  = (
            True                   if pattern == "all"         else
            s["is_nr7"]            if pattern == "nr7"         else
            s["is_nr4"]            if pattern == "nr4"         else
            s["is_vcp"]            if pattern == "vcp"         else
            s["is_pocket_pivot"]   if pattern == "pocketpivot" else
            s["is_rs_div"]         if pattern == "rsdiv"       else True
        )
        rrg_ok  = rrg_quadrant == "all" or s["rrg_quadrant"] == rrg_quadrant
        dma_ok  = (
            True                                              if dma_filter == "all"      else
            s["above20dma"]                                   if dma_filter == "above20"  else
            s["above50dma"]                                   if dma_filter == "above50"  else
            s["above200dma"]                                  if dma_filter == "above200" else
            (s["above20dma"] and s["above50dma"] and s["above200dma"]) if dma_filter == "allAbove" else True
        )
        if all([rsi_ok, mom_ok, vol_ok, pat_ok, rrg_ok, dma_ok]):
            sect_str = sector_mom_map.get(s["sector"], 50.0)
            g = assign_grade(sect_str, s["momentum"], s["rs"] + 50)
            s["grade"] = g["grade"]
            s["grade_desc"] = g["description"]
            filtered.append(s)

    return filtered
