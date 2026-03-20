"""
Technical Indicators — Python port of lib/technical-indicators.ts
All functions operate on plain Python lists or numpy arrays.
"""

import math
import numpy as np
from typing import List


# ── Moving Averages ────────────────────────────────────────────────────────────

def calculate_sma(data: List[float], period: int) -> List[float]:
    result = [float("nan")] * len(data)
    for i in range(period - 1, len(data)):
        result[i] = sum(data[i - period + 1 : i + 1]) / period
    return result


def calculate_ema(data: List[float], period: int) -> List[float]:
    result = [float("nan")] * len(data)
    if len(data) < period:
        return result
    multiplier = 2.0 / (period + 1)
    ema = sum(data[:period]) / period
    result[period - 1] = ema
    for i in range(period, len(data)):
        ema = (data[i] - ema) * multiplier + ema
        result[i] = ema
    return result


# ── RSI (Wilder's Smoothing) ───────────────────────────────────────────────────

def calculate_rsi(closes: List[float], period: int = 14) -> List[float]:
    """
    Wilder's RSI — matches TradingView/Bloomberg output.
    Simple rolling-average RSI diverges by 2-5 pts at extremes; this does not.
    """
    n = len(closes)
    result = [float("nan")] * n
    if n < period + 1:
        return result

    changes = [closes[i] - closes[i - 1] for i in range(1, n)]

    # Seed: simple average of first `period` changes
    avg_gain = sum(c for c in changes[:period] if c > 0) / period
    avg_loss = sum(abs(c) for c in changes[:period] if c < 0) / period

    if avg_loss == 0:
        result[period] = 100.0
    else:
        result[period] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)

    # Wilder smoothing
    for i in range(period + 1, n):
        c = changes[i - 1]
        gain = c if c > 0 else 0.0
        loss = abs(c) if c < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            result[i] = 100.0
        else:
            result[i] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)

    return result


# ── DMA Status ─────────────────────────────────────────────────────────────────

def calculate_dma_status(closes: List[float]) -> dict:
    sma20  = calculate_sma(closes, 20)
    sma50  = calculate_sma(closes, 50)
    sma200 = calculate_sma(closes, 200)
    last   = closes[-1]
    d20    = sma20[-1]
    d50    = sma50[-1]
    d200   = sma200[-1]
    return {
        "above20":  last > d20  if not math.isnan(d20)  else False,
        "above50":  last > d50  if not math.isnan(d50)  else False,
        "above200": last > d200 if not math.isnan(d200) else False,
        "dma20":  0.0 if math.isnan(d20)  else d20,
        "dma50":  0.0 if math.isnan(d50)  else d50,
        "dma200": 0.0 if math.isnan(d200) else d200,
    }


# ── Pattern Detection ──────────────────────────────────────────────────────────

def detect_nr7(data: List[dict]) -> List[bool]:
    """NR7: today's high-low range is narrowest of last 7 days."""
    result = [False] * len(data)
    for i in range(6, len(data)):
        ranges = [data[j]["high"] - data[j]["low"] for j in range(i - 6, i + 1)]
        cur = ranges[-1]
        result[i] = all(r > cur for r in ranges[:-1])
    return result


def detect_nr4(data: List[dict]) -> List[bool]:
    """NR4: today's range is narrowest of last 4 days (tighter signal)."""
    result = [False] * len(data)
    for i in range(3, len(data)):
        ranges = [data[j]["high"] - data[j]["low"] for j in range(i - 3, i + 1)]
        cur = ranges[-1]
        result[i] = all(r > cur for r in ranges[:-1])
    return result


def detect_vcp(data: List[dict], min_contractions: int = 3) -> List[bool]:
    """
    VCP (Minervini): progressively contracting weekly ranges.
    weeklyRanges[0] = newest, weeklyRanges[3] = oldest.
    Contraction = older range > newer range.
    """
    result = [False] * len(data)
    for i in range(30, len(data)):
        weekly = []
        for w in range(4):
            start = i - (w + 1) * 5
            end   = i - w * 5
            if start < 0:
                break
            hi = max(data[d]["high"] for d in range(start, end))
            lo = min(data[d]["low"]  for d in range(start, end))
            weekly.append(hi - lo)

        contractions = sum(1 for r in range(1, len(weekly)) if weekly[r] > weekly[r - 1])
        result[i] = contractions >= min_contractions - 1
    return result


def detect_pocket_pivot(data: List[dict], lookback: int = 10) -> List[bool]:
    """Pocket Pivot (Kacher-Morales): up-day vol > max down-day vol in prior 10 sessions."""
    result = [False] * len(data)
    for i in range(lookback, len(data)):
        if data[i]["close"] <= data[i - 1]["close"]:
            continue
        max_down_vol = 0
        for j in range(i - lookback, i):
            if j > 0 and data[j]["close"] < data[j - 1]["close"]:
                max_down_vol = max(max_down_vol, data[j]["volume"])
        result[i] = data[i]["volume"] > max_down_vol > 0
    return result


def detect_rs_divergence(stock_data: List[dict], bench_data: List[dict], lookback: int = 20) -> List[bool]:
    """
    RS Divergence: RS line making new high while price has not yet made new high.
    (RS leading price — a bullish setup signal.)
    """
    result = [False] * len(stock_data)
    min_len = min(len(stock_data), len(bench_data))
    rs_line = [stock_data[i]["close"] / bench_data[i]["close"] for i in range(min_len)]

    for i in range(lookback, min_len):
        price_high = max(d["high"] for d in stock_data[i - lookback : i])
        is_price_at_high = stock_data[i]["close"] >= price_high * 0.98
        rs_slice = rs_line[i - lookback : i]
        is_rs_at_high = rs_line[i] >= max(rs_slice) * 0.98
        result[i] = not is_price_at_high and is_rs_at_high
    return result


# ── Momentum Score ─────────────────────────────────────────────────────────────

def calculate_momentum_score(data: List[dict]) -> float:
    closes  = [d["close"] for d in data]
    volumes = [d["volume"] for d in data]
    score   = 0.0

    # RSI component (0-25)
    rsi_vals = calculate_rsi(closes)
    last_rsi = rsi_vals[-1]
    if not math.isnan(last_rsi):
        if 50 <= last_rsi <= 70: score += 25
        elif last_rsi > 70:      score += 15
        elif last_rsi >= 40:     score += 10

    # DMA component (0-25)
    dma = calculate_dma_status(closes)
    if dma["above20"]:  score += 10
    if dma["above50"]:  score += 10
    if dma["above200"]: score += 5

    # 20-day price performance (0-25)
    if len(closes) >= 20:
        chg = (closes[-1] - closes[-20]) / closes[-20]
        if chg > 0.10:   score += 25
        elif chg > 0.05: score += 20
        elif chg > 0:    score += 10

    # Volume surge (0-25)
    if len(volumes) >= 20:
        avg    = sum(volumes[-20:]) / 20
        recent = sum(volumes[-5:])  / 5
        if recent > avg * 1.5: score += 25
        elif recent > avg:     score += 15
        else:                  score += 5

    return min(100.0, score)


# ── Relative Strength ──────────────────────────────────────────────────────────

def calculate_relative_strength(stock_closes: List[float], bench_closes: List[float], period: int = 50) -> float:
    if len(stock_closes) < period or len(bench_closes) < period:
        return 0.0
    sr = (stock_closes[-1] - stock_closes[-period]) / stock_closes[-period]
    br = (bench_closes[-1] - bench_closes[-period]) / bench_closes[-period]
    return ((1 + sr) / (1 + br) - 1) * 100


# ── RRG Values (JdK Method) ────────────────────────────────────────────────────

def calculate_rrg_values(stock_closes: List[float], bench_closes: List[float], period: int = 10) -> dict:
    """
    JdK RS-Ratio    = 100 * (RS / SMA(RS, period))
    JdK RS-Momentum = 100 * (RS-Ratio / SMA(RS-Ratio, period))

    Clamped to [85, 115] for display.
    """
    if len(stock_closes) < period * 3 or len(bench_closes) < period * 3:
        return {"rs_ratio": 100.0, "rs_momentum": 100.0}

    n = min(len(stock_closes), len(bench_closes))
    rs_line = [stock_closes[i] / bench_closes[i] for i in range(n)]

    rs_ma = calculate_sma(rs_line, period)
    rs_ratio_line = [
        (rs_line[i] / rs_ma[i]) * 100 if not math.isnan(rs_ma[i]) and rs_ma[i] != 0 else float("nan")
        for i in range(n)
    ]

    filled = [0.0 if math.isnan(v) else v for v in rs_ratio_line]
    rs_ratio_ma = calculate_sma(filled, period)

    last_ratio = rs_ratio_line[-1]
    last_ratio_ma = rs_ratio_ma[-1]

    rs_ratio   = 100.0 if math.isnan(last_ratio) else last_ratio
    rs_momentum = (
        100.0 if math.isnan(last_ratio_ma) or last_ratio_ma == 0 or math.isnan(last_ratio)
        else (last_ratio / last_ratio_ma) * 100
    )

    return {
        "rs_ratio":    max(85.0, min(115.0, rs_ratio)),
        "rs_momentum": max(85.0, min(115.0, rs_momentum)),
    }


def get_rrg_quadrant(rs_ratio: float, rs_momentum: float) -> str:
    if rs_ratio >= 100 and rs_momentum >= 100: return "Leading"
    if rs_ratio >= 100 and rs_momentum < 100:  return "Weakening"
    if rs_ratio < 100  and rs_momentum < 100:  return "Lagging"
    return "Improving"


# ── Volume Ratio ───────────────────────────────────────────────────────────────

def calculate_volume_ratio(volumes: List[float]) -> float:
    if len(volumes) < 20:
        return 1.0
    avg = sum(volumes[-20:]) / 20
    return volumes[-1] / avg if avg > 0 else 1.0


# ── Grade ──────────────────────────────────────────────────────────────────────

def assign_grade(sector_strength: float, stock_momentum: float, rs_rank: float) -> dict:
    if sector_strength > 60 and stock_momentum > 70 and rs_rank > 70:
        return {"grade": "A", "description": "Strong sector + strong stock + high momentum"}
    if sector_strength > 50 and stock_momentum > 40:
        return {"grade": "B", "description": "Strong sector, moderate stock strength"}
    return {"grade": "C", "description": "Weak sector or low momentum"}
