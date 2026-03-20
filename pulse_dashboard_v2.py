"""
Pulse — Nifty Sector Analytics Dashboard  v2
Bloomberg-style dark terminal with auto-refresh, treemap heatmap,
sparkline index bar, RSI gauges, EMA candlesticks, color tables.

Run:  streamlit run pulse_dashboard.py
"""

import math, time
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data_fetcher import (
    fetch_chart, fetch_all_sectors, fetch_indices,
    fetch_sector_data, fetch_screener,
)
from technical_indicators import (
    detect_nr7, detect_nr4, calculate_ema, calculate_rsi,
)

# ── Config ─────────────────────────────────────────────────────────────────────
AUTO_REFRESH_SECS = 60

st.set_page_config(
    page_title="Pulse · Nifty Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap');

/* ── Base ── */
html, body, [data-testid="stAppViewContainer"] {
    background: #060a0f !important;
    font-family: 'Inter', sans-serif;
}
[data-testid="stHeader"]        { background: #060a0f !important; }
[data-testid="stSidebar"]       { background: #0d1117 !important; }
.block-container                { padding: 0.5rem 1.5rem 2rem !important; max-width: 100% !important; }
section[data-testid="stMain"]   { background: #060a0f; }

/* ── Tabs ── */
[data-testid="stTabs"] button {
    color: #8b949e !important; font-size: 0.82rem !important;
    font-weight: 600 !important; letter-spacing: .04em;
    padding: 8px 18px !important; border-radius: 6px 6px 0 0 !important;
    border: none !important; background: transparent !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #f0a500 !important; background: #0d1117 !important;
    border-bottom: 2px solid #f0a500 !important;
}

/* ── Metrics ── */
div[data-testid="metric-container"] {
    background: #0d1117 !important; border: 1px solid #21262d !important;
    border-radius: 8px !important; padding: 12px 14px !important;
}
div[data-testid="metric-container"] label {
    color: #8b949e !important; font-size: 0.7rem !important;
    font-weight: 600 !important; letter-spacing: .06em !important; text-transform: uppercase;
}
div[data-testid="metric-container"] [data-testid="metric-value"] {
    color: #e6edf3 !important; font-size: 1.15rem !important;
    font-weight: 700 !important; font-family: 'JetBrains Mono', monospace !important;
}
[data-testid="metric-delta"] svg { display: none; }
[data-testid="metric-delta"]     { font-size: 0.78rem !important; font-weight: 600 !important; }

/* ── Tables / Dataframes ── */
[data-testid="stDataFrame"] { border: 1px solid #21262d !important; border-radius: 8px !important; }
.stDataFrame iframe { background: #0d1117 !important; }

/* ── Expanders ── */
details > summary {
    background: #0d1117 !important; border: 1px solid #21262d !important;
    border-radius: 8px !important; padding: 10px 14px !important;
    color: #e6edf3 !important; font-weight: 600 !important; font-size: 0.85rem !important;
}
details[open] > summary { border-radius: 8px 8px 0 0 !important; }
details > div { background: #0d1117 !important; border: 1px solid #21262d !important; border-top: none !important; border-radius: 0 0 8px 8px !important; padding: 14px !important; }

/* ── Buttons ── */
[data-testid="stButton"] button {
    background: #161b22 !important; color: #e6edf3 !important;
    border: 1px solid #30363d !important; border-radius: 6px !important;
    font-size: 0.8rem !important; font-weight: 600 !important;
    padding: 6px 14px !important; transition: all .2s !important;
}
[data-testid="stButton"] button:hover {
    background: #21262d !important; border-color: #f0a500 !important;
    color: #f0a500 !important;
}

/* ── Selectbox / Slider ── */
[data-testid="stSelectbox"] > div > div {
    background: #0d1117 !important; border: 1px solid #30363d !important;
    border-radius: 6px !important; color: #e6edf3 !important; font-size: 0.82rem !important;
}
[data-testid="stSlider"] > div > div > div { background: #f0a500 !important; }

/* ── Progress bar ── */
[data-testid="stProgressBar"] > div { background: #21262d !important; }
[data-testid="stProgressBar"] > div > div { background: linear-gradient(90deg, #f0a500, #f59e0b) !important; }

/* ── Spinners / info ── */
[data-testid="stSpinner"] > div { color: #f0a500 !important; }
[data-testid="stAlert"] { background: #0d1117 !important; border: 1px solid #30363d !important; color: #e6edf3 !important; }

/* ── Custom components ── */

/* Ticker tape */
.ticker-wrap {
    overflow: hidden; background: #0d1117;
    border-top: 1px solid #21262d; border-bottom: 1px solid #21262d;
    padding: 6px 0; margin: 0 -1.5rem 12px; white-space: nowrap;
}
.ticker-inner {
    display: inline-block; animation: ticker 40s linear infinite;
}
@keyframes ticker { from { transform: translateX(0); } to { transform: translateX(-50%); } }
.ticker-item {
    display: inline-block; padding: 0 28px;
    font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; font-weight: 600;
}

/* Header */
.pulse-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 0 8px; border-bottom: 1px solid #21262d; margin-bottom: 10px;
}
.pulse-logo { font-size: 1.5rem; font-weight: 800; letter-spacing: -.03em; color: #f0a500; font-family: 'Inter', sans-serif; }
.pulse-logo span { color: #e6edf3; }
.pulse-sub  { font-size: 0.7rem; color: #8b949e; letter-spacing: .08em; text-transform: uppercase; margin-top: 1px; }

/* Countdown ring */
.timer-wrap { display: flex; align-items: center; gap: 10px; }
.timer-ring  { position: relative; width: 40px; height: 40px; }
.timer-ring svg { transform: rotate(-90deg); }
.timer-ring .bg { fill: none; stroke: #21262d; stroke-width: 3.5; }
.timer-ring .fg { fill: none; stroke: #f0a500; stroke-width: 3.5; stroke-linecap: round;
    stroke-dasharray: 100; transition: stroke-dashoffset .9s linear; }
.timer-label { position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
    font-size: 0.6rem; font-weight: 700; color: #f0a500; font-family: 'JetBrains Mono', monospace; }
.live-dot { width: 7px; height: 7px; border-radius: 50%; background: #22c55e;
    box-shadow: 0 0 0 0 rgba(34,197,94,.6); animation: pulse-dot 2s ease-in-out infinite; }
@keyframes pulse-dot { 0%,100%{box-shadow:0 0 0 0 rgba(34,197,94,.5)} 50%{box-shadow:0 0 0 6px rgba(34,197,94,0)} }

/* Index card */
.idx-card {
    background: #0d1117; border: 1px solid #21262d; border-radius: 8px;
    padding: 10px 14px; position: relative; overflow: hidden;
}
.idx-card:hover { border-color: #30363d; }
.idx-name  { font-size: 0.68rem; color: #8b949e; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; }
.idx-price { font-size: 1.18rem; font-weight: 700; color: #e6edf3; font-family: 'JetBrains Mono', monospace; margin: 3px 0; }
.idx-chg   { font-size: 0.78rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.idx-rsi   { font-size: 0.67rem; color: #8b949e; margin-top: 4px; }
.idx-bar   { position: absolute; bottom: 0; left: 0; right: 0; height: 3px; }

/* Sector heatmap cells */
.heat-cell {
    border-radius: 8px; padding: 14px 12px; position: relative; overflow: hidden;
    transition: transform .15s, box-shadow .15s; cursor: pointer;
    border: 1px solid rgba(255,255,255,0.06);
}
.heat-cell:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,.5); }
.heat-name  { font-size: 0.8rem; font-weight: 700; color: #fff; margin-bottom: 4px; }
.heat-chg   { font-size: 1.25rem; font-weight: 800; color: #fff; font-family: 'JetBrains Mono', monospace; }
.heat-stats { display: flex; gap: 14px; margin-top: 8px; }
.heat-stat  { font-size: 0.67rem; color: rgba(255,255,255,0.7); }
.heat-stat b{ color: #fff; }
.heat-badge { font-size: 0.65rem; font-weight: 700; padding: 2px 6px; border-radius: 3px;
    margin-top: 6px; display: inline-block; }
.heat-bar   { position: absolute; bottom: 0; left: 0; right: 0; height: 3px; background: rgba(0,0,0,0.3); }
.heat-fill  { height: 100%; background: rgba(255,255,255,0.5); border-radius: 2px; }
.heat-shine { position: absolute; top: 0; left: 0; right: 0; height: 40%;
    background: linear-gradient(to bottom, rgba(255,255,255,0.08), transparent); border-radius: 8px 8px 0 0; }

/* Signal badges */
.sig { display: inline-block; padding: 3px 9px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; margin: 2px; }
.sig-nr7   { background: #431407; color: #fb923c; border: 1px solid #7c2d12; }
.sig-nr4   { background: #3f1010; color: #fca5a5; border: 1px solid #991b1b; }
.sig-vcp   { background: #1e1030; color: #c084fc; border: 1px solid #6d28d9; }
.sig-pp    { background: #052e16; color: #86efac; border: 1px solid #166534; }
.sig-rsdiv { background: #082f49; color: #7dd3fc; border: 1px solid #0369a1; }

/* Grade pill */
.grade-A { background: #052e16; color: #4ade80; border: 1px solid #166534; border-radius: 12px; padding: 2px 10px; font-weight: 800; font-size: 0.78rem; }
.grade-B { background: #431407; color: #fb923c; border: 1px solid #7c2d12; border-radius: 12px; padding: 2px 10px; font-weight: 800; font-size: 0.78rem; }
.grade-C { background: #0f172a; color: #94a3b8; border: 1px solid #1e293b; border-radius: 12px; padding: 2px 10px; font-weight: 800; font-size: 0.78rem; }

/* Stock detail card */
.stock-card {
    background: #0d1117; border: 1px solid #21262d; border-radius: 10px;
    padding: 20px; margin-top: 12px;
}
.stock-symbol { font-size: 1.6rem; font-weight: 800; color: #e6edf3; font-family: 'JetBrains Mono', monospace; }
.stock-name   { font-size: 0.82rem; color: #8b949e; margin-top: 2px; }
.stock-price  { font-size: 2rem; font-weight: 700; color: #e6edf3; font-family: 'JetBrains Mono', monospace; }

/* Section headers */
.section-hdr {
    font-size: 0.7rem; font-weight: 700; color: #8b949e;
    letter-spacing: .1em; text-transform: uppercase;
    border-left: 3px solid #f0a500; padding-left: 8px; margin: 14px 0 8px;
}

/* MA row */
.ma-row  { display: flex; gap: 10px; }
.ma-card { flex: 1; background: #161b22; border-radius: 6px; padding: 8px 10px; border: 1px solid #21262d; }
.ma-lbl  { font-size: 0.67rem; color: #8b949e; font-weight: 600; }
.ma-val  { font-size: 0.85rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; color: #e6edf3; margin-top: 2px; }
.ma-stat { font-size: 0.7rem; font-weight: 700; margin-top: 3px; }
.above   { color: #4ade80; }
.below   { color: #f87171; }

/* EMA strip */
.ema-strip { display: flex; gap: 8px; }
.ema-chip  { background: #161b22; border: 1px solid #21262d; border-radius: 5px; padding: 6px 10px; }
.ema-lbl   { font-size: 0.62rem; font-weight: 700; }
.ema-val   { font-size: 0.8rem; font-weight: 600; font-family: 'JetBrains Mono', monospace; color: #e6edf3; }

/* 52w range */
.range-bar { background: linear-gradient(90deg, #f87171 0%, #fbbf24 50%, #4ade80 100%);
    height: 6px; border-radius: 3px; position: relative; margin: 6px 0; }
.range-dot { position: absolute; top: 50%; transform: translate(-50%,-50%);
    width: 14px; height: 14px; border-radius: 50%; background: #fff;
    border: 2px solid #060a0f; box-shadow: 0 0 0 2px #f0a500; }

/* Screener filter pill */
.filter-active { background: #1c1205; border: 1px solid #f0a500; border-radius: 20px; padding: 4px 12px;
    font-size: 0.72rem; color: #f0a500; font-weight: 700; display: inline-block; margin: 2px; }

/* Scrollbar */
::-webkit-scrollbar       { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }

/* Divider */
.pulse-divider { border: none; border-top: 1px solid #21262d; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# ── Constants & helpers ────────────────────────────────────────────────────────

PLOTLY_THEME = dict(
    paper_bgcolor="#060a0f", plot_bgcolor="#0d1117",
    font=dict(color="#e6edf3", family="JetBrains Mono, monospace", size=11),
)

def fmt_pct(v):
    if math.isnan(v): return "—"
    return f"+{v:.2f}%" if v >= 0 else f"{v:.2f}%"

def fmt_inr(v):
    return f"₹{v:,.2f}"

def pct_color(v):
    return "#4ade80" if v >= 0 else "#f87171"

def rrg_color(q):
    return {"Leading":"#22c55e","Weakening":"#eab308","Lagging":"#ef4444","Improving":"#3b82f6"}.get(q,"#8b949e")

def heat_bg(chg):
    if chg >= 2:    return "linear-gradient(135deg,#065f46,#047857)"
    if chg >= 1:    return "linear-gradient(135deg,#047857,#059669)"
    if chg >= 0.5:  return "linear-gradient(135deg,#064e3b,#047857)"
    if chg >= 0:    return "linear-gradient(135deg,#062316,#083d27)"
    if chg >= -0.5: return "linear-gradient(135deg,#2d0707,#3f0d0d)"
    if chg >= -1:   return "linear-gradient(135deg,#450a0a,#7f1d1d)"
    return             "linear-gradient(135deg,#7f1d1d,#991b1b)"

def rsi_gauge_color(rsi):
    if math.isnan(rsi): return "#8b949e"
    if rsi >= 70: return "#f59e0b"
    if rsi <= 30: return "#3b82f6"
    return "#4ade80"


# ── Auto-refresh logic ─────────────────────────────────────────────────────────

def init_timer():
    if "last_refresh"  not in st.session_state: st.session_state.last_refresh  = time.time()
    if "refresh_count" not in st.session_state: st.session_state.refresh_count = 0

def check_auto_refresh():
    elapsed = time.time() - st.session_state.last_refresh
    if elapsed >= AUTO_REFRESH_SECS:
        st.session_state.last_refresh  = time.time()
        st.session_state.refresh_count += 1
        st.cache_data.clear()
        st.rerun()
    return elapsed

def countdown_html(elapsed: float) -> str:
    remaining  = max(0, AUTO_REFRESH_SECS - elapsed)
    pct        = remaining / AUTO_REFRESH_SECS
    dash_off   = 100 - int(pct * 100)
    secs_label = f"{int(remaining):02d}"
    now_str    = time.strftime("%H:%M:%S")
    return f"""
    <div style="display:flex;align-items:center;gap:14px;">
      <div style="display:flex;align-items:center;gap:6px;">
        <div class="live-dot"></div>
        <span style="font-size:0.72rem;color:#8b949e;font-weight:600;letter-spacing:.06em">LIVE</span>
      </div>
      <div style="font-size:0.72rem;color:#8b949e;font-family:'JetBrains Mono',monospace">{now_str} IST</div>
      <div class="timer-ring">
        <svg viewBox="0 0 36 36" width="38" height="38">
          <circle class="bg" cx="18" cy="18" r="15.9"/>
          <circle class="fg" cx="18" cy="18" r="15.9" style="stroke-dashoffset:{dash_off}"/>
        </svg>
        <div class="timer-label">{secs_label}</div>
      </div>
    </div>"""


# ── Ticker tape ────────────────────────────────────────────────────────────────

def render_ticker(indices: list):
    items = []
    for idx in indices:
        c   = pct_color(idx["change_pct"])
        arr = "▲" if idx["change_pct"] >= 0 else "▼"
        items.append(
            f'<span class="ticker-item">'
            f'<span style="color:#8b949e">{idx["name"]}</span>'
            f'&nbsp;<span style="color:#e6edf3;font-weight:700">{idx["price"]:,.0f}</span>'
            f'&nbsp;<span style="color:{c}">{arr} {fmt_pct(idx["change_pct"])}</span>'
            f'</span>'
        )
    # Duplicate for seamless loop
    inner = "".join(items * 2)
    st.markdown(
        f'<div class="ticker-wrap"><div class="ticker-inner">{inner}</div></div>',
        unsafe_allow_html=True
    )


# ── Index cards ────────────────────────────────────────────────────────────────

def render_index_cards(indices: list):
    KEY = ("NIFTY 50","NIFTY BANK","NIFTY IT","NIFTY PHARMA","NIFTY AUTO","NIFTY METAL")
    display = [i for i in indices if i["name"] in KEY][:6]
    if not display: display = indices[:6]

    cols = st.columns(len(display))
    for col, idx in zip(cols, display):
        c    = pct_color(idx["change_pct"])
        rsi  = idx.get("rsi", float("nan"))
        rc   = rsi_gauge_color(rsi)
        rsi_str = f"{rsi:.0f}" if not math.isnan(rsi) else "—"
        bar_pct = int(max(0, min(100, ((idx["price"] - idx.get("low52w", idx["price"])) /
                   max(1, idx.get("high52w", idx["price"]) - idx.get("low52w", idx["price"]))) * 100))) if idx.get("high52w") else 50

        col.markdown(f"""
        <div class="idx-card">
          <div class="idx-name">{idx['name']}</div>
          <div class="idx-price">{idx['price']:,.0f}</div>
          <div class="idx-chg" style="color:{c}">{fmt_pct(idx['change_pct'])}
            &nbsp;<span style="color:#8b949e;font-size:0.65rem;font-weight:500">{idx['change']:+,.0f}</span>
          </div>
          <div class="idx-rsi">RSI <span style="color:{rc};font-weight:700">{rsi_str}</span></div>
          <div class="idx-bar" style="background:#21262d">
            <div style="height:100%;width:{bar_pct}%;background:{c};border-radius:0 0 8px 8px;opacity:.7"></div>
          </div>
        </div>""", unsafe_allow_html=True)


# ── Sector heatmap (Plotly treemap) ───────────────────────────────────────────

def render_heatmap_plotly(sectors: list) -> go.Figure:
    labels, values, colors, texts, parents = [], [], [], [], []
    for s in sectors:
        chg   = s["change"]
        color = "#065f46" if chg >= 2 else "#047857" if chg >= 1 else "#059669" if chg >= .5 \
                else "#083d27" if chg >= 0 else "#450a0a" if chg >= -1 else "#7f1d1d"
        labels.append(s["name"])
        values.append(max(1, s["stock_count"]))
        colors.append(color)
        parents.append("")
        texts.append(
            f"<b>{s['name']}</b><br>{fmt_pct(chg)}<br>"
            f"RSI {s['rsi']:.0f} · Breadth {s['breadth']:.0f}%<br>{s.get('rrg_quadrant','')}"
        )

    fig = go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values,
        text=texts, textinfo="text",
        marker=dict(colors=colors, line=dict(width=2, color="#060a0f")),
        hovertemplate="<b>%{label}</b><br>%{text}<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_THEME,
        margin=dict(l=0, r=0, t=0, b=0),
        height=320,
    )
    return fig


# ── Sector HTML heatmap (fallback grid) ───────────────────────────────────────

def render_heatmap_grid(sectors: list):
    cols = st.columns(5)
    for i, s in enumerate(sectors):
        bg  = heat_bg(s["change"])
        qc  = rrg_color(s.get("rrg_quadrant","Lagging"))
        mom = int(s.get("momentum", 50))
        with cols[i % 5]:
            st.markdown(f"""
            <div class="heat-cell" style="background:{bg};min-height:110px">
              <div class="heat-shine"></div>
              <div class="heat-name">{s['name']}</div>
              <div class="heat-chg">{fmt_pct(s['change'])}</div>
              <div class="heat-stats">
                <div class="heat-stat">RSI <b>{s['rsi']:.0f}</b></div>
                <div class="heat-stat">Breadth <b>{s['breadth']:.0f}%</b></div>
              </div>
              <span class="heat-badge" style="background:rgba(0,0,0,0.35);color:{qc}">{s.get('rrg_quadrant','')}</span>
              <div class="heat-bar"><div class="heat-fill" style="width:{mom}%"></div></div>
            </div>""", unsafe_allow_html=True)
            if st.button("⤵", key=f"hd_{s['name']}", help=f"Drill into {s['name']}", use_container_width=True):
                st.session_state["selected_sector"] = s["name"]
                st.rerun()


# ── Candlestick with EMA overlay + RS line ────────────────────────────────────

def render_candlestick(ohlcv: list, symbol: str) -> go.Figure:
    if not ohlcv: return go.Figure()
    df = pd.DataFrame(ohlcv)
    df["date"] = pd.to_datetime(df["date"])

    closes  = df["close"].tolist()
    volumes = df["volume"].tolist()

    ema10 = calculate_ema(closes, 10)
    ema21 = calculate_ema(closes, 21)
    ema50 = calculate_ema(closes, 50)

    nr7_dates = [df["date"].iloc[i] for i, v in enumerate(detect_nr7(ohlcv)) if v]
    nr4_dates = [df["date"].iloc[i] for i, v in enumerate(detect_nr4(ohlcv)) if v]
    nr7_lows  = [df["low"].iloc[i] * 0.997 for i, v in enumerate(detect_nr7(ohlcv)) if v]
    nr4_lows  = [df["low"].iloc[i] * 0.994 for i, v in enumerate(detect_nr4(ohlcv)) if v]

    vol_colors = ["#4ade80" if c >= o else "#f87171" for c, o in zip(closes, df["open"].tolist())]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.73, 0.27], vertical_spacing=0.01,
        subplot_titles=["", ""]
    )

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"],
        low=df["low"], close=closes,
        name=symbol.replace(".NS",""),
        increasing=dict(line=dict(color="#4ade80", width=1), fillcolor="#4ade80"),
        decreasing=dict(line=dict(color="#f87171", width=1), fillcolor="#f87171"),
    ), row=1, col=1)

    # EMA overlays
    for ema, color, name in [(ema10,"#38bdf8","EMA10"),(ema21,"#a78bfa","EMA21"),(ema50,"#fb923c","EMA50")]:
        valid = [(d, v) for d, v in zip(df["date"], ema) if not math.isnan(v)]
        if valid:
            xs, ys = zip(*valid)
            fig.add_trace(go.Scatter(x=list(xs), y=list(ys), mode="lines",
                line=dict(color=color, width=1.2), name=name, opacity=0.85), row=1, col=1)

    # NR7 / NR4 markers
    if nr7_dates:
        fig.add_trace(go.Scatter(x=nr7_dates, y=nr7_lows, mode="markers",
            marker=dict(symbol="triangle-up", size=9, color="#f59e0b"),
            name="NR7", showlegend=True), row=1, col=1)
    if nr4_dates:
        fig.add_trace(go.Scatter(x=nr4_dates, y=nr4_lows, mode="markers",
            marker=dict(symbol="triangle-up", size=7, color="#f97316"),
            name="NR4", showlegend=True), row=1, col=1)

    # Volume
    fig.add_trace(go.Bar(x=df["date"], y=volumes, name="Volume",
        marker_color=vol_colors, opacity=0.65), row=2, col=1)

    fig.update_layout(
        **PLOTLY_THEME,
        height=440, margin=dict(l=10, r=10, t=10, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.04, x=0, bgcolor="rgba(0,0,0,0)",
            font=dict(size=10), itemsizing="constant"),
        hovermode="x unified",
    )
    for r in [1, 2]:
        fig.update_xaxes(gridcolor="#1a2030", showgrid=True, row=r, col=1, zeroline=False)
        fig.update_yaxes(gridcolor="#1a2030", showgrid=True, row=r, col=1, zeroline=False, tickfont=dict(size=10))
    return fig


# ── RSI Gauge ─────────────────────────────────────────────────────────────────

def rsi_gauge(rsi: float) -> go.Figure:
    color = rsi_gauge_color(rsi)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=rsi if not math.isnan(rsi) else 50,
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor="#30363d",
                tickfont=dict(size=9, color="#8b949e"),
                tickvals=[0, 30, 50, 70, 100]),
            bar=dict(color=color, thickness=0.3),
            bgcolor="#0d1117", borderwidth=0,
            steps=[
                dict(range=[0,  30], color="#082f49"),
                dict(range=[30, 70], color="#161b22"),
                dict(range=[70,100], color="#431407"),
            ],
            threshold=dict(line=dict(color=color, width=2), thickness=0.75, value=rsi)
        ),
        number=dict(font=dict(size=22, color=color, family="JetBrains Mono")),
        title=dict(text="RSI (14)", font=dict(size=10, color="#8b949e")),
        domain=dict(x=[0,1], y=[0,1])
    ))
    fig.update_layout(**PLOTLY_THEME, height=130, margin=dict(l=10, r=10, t=20, b=0))
    return fig


# ── Momentum donut ────────────────────────────────────────────────────────────

def momentum_donut(score: float) -> go.Figure:
    color = "#4ade80" if score >= 70 else "#f59e0b" if score >= 40 else "#f87171"
    fig = go.Figure(go.Pie(
        values=[score, 100 - score],
        hole=0.72, showlegend=False,
        marker=dict(colors=[color, "#161b22"]),
        textinfo="none",
    ))
    fig.add_annotation(text=f"<b>{score:.0f}</b>", x=0.5, y=0.5, showarrow=False,
        font=dict(size=20, color=color, family="JetBrains Mono"))
    fig.add_annotation(text="MOM", x=0.5, y=0.22, showarrow=False,
        font=dict(size=9, color="#8b949e"))
    fig.update_layout(**PLOTLY_THEME, height=130, margin=dict(l=0, r=0, t=10, b=0))
    return fig


# ── RRG Chart ─────────────────────────────────────────────────────────────────

def render_rrg(sectors: list) -> go.Figure:
    fig = go.Figure()

    # Quadrant fills
    for x0, x1, y0, y1, c in [
        (100,115,100,115,"rgba(34,197,94,0.07)"),
        (100,115, 85,100,"rgba(234,179,8,0.07)"),
        ( 85,100, 85,100,"rgba(239,68,68,0.07)"),
        ( 85,100,100,115,"rgba(59,130,246,0.07)"),
    ]:
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
            fillcolor=c, line=dict(width=0), layer="below")

    for s in sectors:
        q  = s.get("rrg_quadrant","Lagging")
        c  = rrg_color(q)
        rx, rm = s.get("rs_ratio",100), s.get("rs_momentum",100)
        fig.add_trace(go.Scatter(
            x=[rx], y=[rm], mode="markers+text",
            marker=dict(size=16, color=c, line=dict(width=2.5, color="#060a0f"),
                symbol="circle"),
            text=[f"  {s['name']}"],
            textposition="middle right",
            textfont=dict(size=11, color="#e6edf3", family="Inter"),
            name=s["name"],
            hovertemplate=(
                f"<b>{s['name']}</b><br>"
                f"RS-Ratio: {rx:.2f}<br>"
                f"RS-Momentum: {rm:.2f}<br>"
                f"Quadrant: <b>{q}</b><extra></extra>"
            ),
        ))

    fig.add_hline(y=100, line=dict(color="#30363d", dash="dot", width=1))
    fig.add_vline(x=100, line=dict(color="#30363d", dash="dot", width=1))

    for x, y, lbl, c in [
        (86.5,114,"IMPROVING","#3b82f6"),
        (114,  114,"LEADING",  "#22c55e"),
        (114,   86,"WEAKENING","#eab308"),
        (86.5,  86,"LAGGING",  "#ef4444"),
    ]:
        fig.add_annotation(x=x, y=y, text=lbl, showarrow=False,
            font=dict(size=8.5, color=c, family="Inter"), opacity=0.55)

    fig.update_layout(
        **PLOTLY_THEME,
        xaxis=dict(title="← Lagging  |  RS-Ratio  |  Leading →",
            gridcolor="#1a2030", range=[85,115],
            title_font=dict(size=10, color="#8b949e"),
            tickfont=dict(size=9)),
        yaxis=dict(title="RS-Momentum",
            gridcolor="#1a2030", range=[85,115],
            title_font=dict(size=10, color="#8b949e"),
            tickfont=dict(size=9)),
        showlegend=False,
        height=500,
        margin=dict(l=55, r=30, t=15, b=55),
        hovermode="closest",
    )
    return fig


# ── Stock detail card ─────────────────────────────────────────────────────────

def render_stock_detail(stock: dict):
    sym   = stock["symbol"].replace(".NS","")
    price = stock["price"]
    chg   = stock["change_pct"]
    cc    = pct_color(chg)
    rsi   = stock.get("rsi", float("nan"))
    mom   = stock.get("momentum", 0)
    volr  = stock.get("vol_ratio", 1)
    rs    = stock.get("rs", 0)

    # Badges
    badges_html = ""
    for flag, cls, label in [
        (stock.get("is_nr7"),        "sig-nr7",  "NR7"),
        (stock.get("is_nr4"),        "sig-nr4",  "NR4"),
        (stock.get("is_vcp"),        "sig-vcp",  "VCP"),
        (stock.get("is_pocket_pivot"),"sig-pp",  "Pocket Pivot"),
        (stock.get("is_rs_div"),     "sig-rsdiv","RS Divergence"),
    ]:
        if flag: badges_html += f'<span class="sig {cls}">{label}</span>'

    rrg_q = stock.get("rrg_quadrant","—")
    rrg_c = rrg_color(rrg_q)
    grade = stock.get("grade","—")
    gcls  = f"grade-{grade}" if grade in ("A","B","C") else "grade-C"

    st.markdown(f"""
    <div class="stock-card">
      <div style="display:flex;align-items:flex-start;justify-content:space-between">
        <div>
          <div style="display:flex;align-items:center;gap:10px">
            <div class="stock-symbol">{sym}</div>
            <span class="{gcls}">{grade}</span>
            <span style="background:rgba(0,0,0,0.3);color:{rrg_c};padding:2px 9px;border-radius:4px;font-size:0.72rem;font-weight:700;border:1px solid {rrg_c}40">{rrg_q}</span>
          </div>
          <div class="stock-name">{stock.get('name','')}</div>
          <div style="margin-top:6px">
            <span class="stock-price">{fmt_inr(price)}</span>
            <span style="color:{cc};font-size:1rem;font-weight:700;font-family:'JetBrains Mono',monospace;margin-left:12px">{fmt_pct(chg)}</span>
          </div>
          <div style="margin-top:8px">{badges_html if badges_html else '<span style="color:#8b949e;font-size:0.75rem">No pattern signals today</span>'}</div>
        </div>
        <div style="text-align:right">
          <div style="font-size:0.68rem;color:#8b949e;margin-bottom:4px">Vol Ratio</div>
          <div style="font-size:1.3rem;font-weight:700;color:{'#4ade80' if volr>1.5 else '#e6edf3'};font-family:'JetBrains Mono',monospace">{volr:.2f}×</div>
          <div style="font-size:0.68rem;color:#8b949e;margin-top:8px">Rel. Strength</div>
          <div style="font-size:1rem;font-weight:700;color:{pct_color(rs)};font-family:'JetBrains Mono',monospace">{rs:+.1f}%</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # RSI gauge + Momentum donut
    g1, g2, g3 = st.columns([1.2, 1.2, 3.6])
    with g1: st.plotly_chart(rsi_gauge(rsi), use_container_width=True, config={"displayModeBar":False})
    with g2: st.plotly_chart(momentum_donut(mom), use_container_width=True, config={"displayModeBar":False})
    with g3:
        # MA status
        st.markdown('<div class="section-hdr">Moving Averages</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="ma-row">
          {''.join([
            f'<div class="ma-card"><div class="ma-lbl">{n} DMA</div>'
            f'<div class="ma-val">{v:.1f}</div>'
            f'<div class="ma-stat {"above" if above else "below"}">{"▲ Above" if above else "▼ Below"}</div></div>'
            for n, v, above in [
                ("20",  stock.get("dma20",0),   stock.get("above20dma",False)),
                ("50",  stock.get("dma50",0),   stock.get("above50dma",False)),
                ("200", stock.get("dma200",0),  stock.get("above200dma",False)),
            ]
          ])}
        </div>""", unsafe_allow_html=True)

        # EMA strip
        st.markdown('<div class="section-hdr" style="margin-top:10px">EMA Values</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="ema-strip">
          {''.join([
            f'<div class="ema-chip"><div class="ema-lbl" style="color:{c}">{n}</div><div class="ema-val">{v:.1f}</div></div>'
            for n, v, c in [
                ("EMA 5",  stock.get("ema5",0),  "#38bdf8"),
                ("EMA 10", stock.get("ema10",0), "#38bdf8"),
                ("EMA 21", stock.get("ema21",0), "#a78bfa"),
                ("EMA 50", stock.get("ema50",0), "#fb923c"),
            ]
          ])}
        </div>""", unsafe_allow_html=True)

    # 52-week range
    lo, hi = stock.get("low52w",0), stock.get("high52w",0)
    pct_pos = int((price - lo) / max(1, hi - lo) * 100) if hi > lo else 50
    st.markdown(f"""
    <div style="margin:12px 0 6px">
      <div class="section-hdr">52-Week Range</div>
      <div style="display:flex;align-items:center;gap:10px;margin-top:4px">
        <span style="font-size:0.75rem;color:#8b949e;font-family:'JetBrains Mono',monospace;min-width:80px">{fmt_inr(lo)}</span>
        <div style="flex:1;position:relative">
          <div class="range-bar"></div>
          <div class="range-dot" style="left:{pct_pos}%"></div>
        </div>
        <span style="font-size:0.75rem;color:#8b949e;font-family:'JetBrains Mono',monospace;min-width:80px;text-align:right">{fmt_inr(hi)}</span>
      </div>
      <div style="text-align:center;font-size:0.7rem;color:{pct_color(chg)};margin-top:2px">{pct_pos:.0f}% of 52w range</div>
    </div>""", unsafe_allow_html=True)

    # Candlestick
    if stock.get("ohlcv"):
        st.markdown('<div class="section-hdr">Price Chart — EMA 10/21/50 · NR7 ▲ · NR4 ▲</div>', unsafe_allow_html=True)
        st.plotly_chart(render_candlestick(stock["ohlcv"], stock["symbol"]),
            use_container_width=True, config={"displayModeBar": False})

    # External links
    st.markdown(
        f'<div style="display:flex;gap:12px;margin-top:6px">'
        f'<a href="https://www.screener.in/company/{sym}/" target="_blank" '
        f'style="font-size:0.78rem;color:#f0a500;text-decoration:none;border:1px solid #f0a50040;'
        f'border-radius:5px;padding:4px 12px">🔗 Screener.in</a>'
        f'<a href="https://in.tradingview.com/chart/?symbol=NSE:{sym}" target="_blank" '
        f'style="font-size:0.78rem;color:#38bdf8;text-decoration:none;border:1px solid #38bdf840;'
        f'border-radius:5px;padding:4px 12px">📈 TradingView</a>'
        f'</div>', unsafe_allow_html=True
    )


# ── Sector summary table (colored) ────────────────────────────────────────────

def render_sector_table(sectors: list) -> pd.DataFrame:
    rows = []
    for s in sectors:
        rows.append({
            "Sector":    s["name"],
            "Change%":   s["change"],
            "RSI":       s["rsi"],
            "Momentum":  s["momentum"],
            "Breadth%":  s["breadth"],
            "VolRatio":  s["vol_ratio"],
            "RRG":       s.get("rrg_quadrant","—"),
            "Stocks":    s.get("stock_count",0),
        })
    return pd.DataFrame(rows)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Session state
    for k, v in [("selected_sector", None), ("selected_stock", None),
                  ("last_refresh", time.time()), ("refresh_count", 0)]:
        if k not in st.session_state: st.session_state[k] = v

    # Auto-refresh check
    elapsed = check_auto_refresh()

    # ── Header ────────────────────────────────────────────────────────────────
    h_left, h_mid, h_right = st.columns([3, 5, 3])
    with h_left:
        st.markdown(
            '<div style="padding-top:6px">'
            '<div class="pulse-logo">⚡ Pulse<span style="opacity:.4">·</span></div>'
            '<div class="pulse-sub">Nifty Sector Analytics</div>'
            '</div>', unsafe_allow_html=True)
    with h_mid:
        pass
    with h_right:
        rc1, rc2 = st.columns([3, 1])
        with rc1:
            st.markdown(countdown_html(elapsed), unsafe_allow_html=True)
        with rc2:
            if st.button("↺", help="Refresh now"):
                st.cache_data.clear()
                st.session_state.last_refresh = time.time()
                st.rerun()

    # ── Load data ──────────────────────────────────────────────────────────────
    with st.spinner(""):
        indices = fetch_indices()
        sectors = fetch_all_sectors()

    # ── Ticker tape ───────────────────────────────────────────────────────────
    if indices: render_ticker(indices)

    # ── Index cards ───────────────────────────────────────────────────────────
    if indices:
        render_index_cards(indices)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_ov, tab_rrg, tab_sc = st.tabs(["  🗺  Sector Overview  ", "  🔄  RRG  ", "  🔍  Screener  "])

    # ═══════════════════════════════════════════════════════════════════════════
    # OVERVIEW TAB
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_ov:
        selected = st.session_state["selected_sector"]

        if selected:
            # ── Sector drill-down ──────────────────────────────────────────
            bc1, bc2 = st.columns([1, 9])
            with bc1:
                if st.button("← Back"):
                    st.session_state.update(selected_sector=None, selected_stock=None)
                    st.rerun()

            with st.spinner(f"Loading {selected}…"):
                detail = fetch_sector_data(selected)

            if detail:
                st.markdown(f'<div style="font-size:1.1rem;font-weight:700;color:#e6edf3;margin-bottom:8px">'
                    f'<span style="color:#f0a500">{selected}</span> Sector</div>', unsafe_allow_html=True)

                m1,m2,m3,m4,m5 = st.columns(5)
                m1.metric("Change",     fmt_pct(detail["change"]))
                m2.metric("RSI",        f"{detail['rsi']:.1f}")
                m3.metric("Momentum",   f"{detail['momentum']:.0f}")
                m4.metric("Breadth",    f"{detail['breadth']:.0f}%")
                m5.metric("Vol Ratio",  f"{detail['vol_ratio']:.2f}×")

                st.markdown('<hr class="pulse-divider"/>', unsafe_allow_html=True)

                if detail["stocks"]:
                    rows = []
                    for s in detail["stocks"]:
                        rows.append({
                            "Symbol":  s["symbol"].replace(".NS",""),
                            "Name":    s["name"],
                            "Price":   s["price"],
                            "Chg%":    s["change_pct"],
                            "RSI":     s["rsi"],
                            "Mom":     s["momentum"],
                            "VolR":    s["vol_ratio"],
                            "RRG":     s["rrg_quadrant"],
                            "20D":     s["above20dma"],
                            "50D":     s["above50dma"],
                            "Signals": " ".join(filter(None,[
                                "NR7" if s["is_nr7"] else "",
                                "NR4" if s["is_nr4"] else "",
                                "VCP" if s["is_vcp"] else "",
                                "PP"  if s["is_pocket_pivot"] else "",
                                "RS↑" if s["is_rs_div"] else "",
                            ])) or "—",
                        })
                    df = pd.DataFrame(rows)
                    sel = st.dataframe(
                        df, use_container_width=True, hide_index=True,
                        on_select="rerun", selection_mode="single-row",
                        column_config={
                            "Price":  st.column_config.NumberColumn(format="₹%.2f"),
                            "Chg%":   st.column_config.NumberColumn(format="%.2f%%"),
                            "RSI":    st.column_config.NumberColumn(format="%.1f"),
                            "Mom":    st.column_config.NumberColumn(format="%.0f"),
                            "VolR":   st.column_config.NumberColumn(format="%.2f×"),
                            "20D":    st.column_config.CheckboxColumn(),
                            "50D":    st.column_config.CheckboxColumn(),
                        }
                    )
                    if sel.selection.rows:
                        s = detail["stocks"][sel.selection.rows[0]]
                        render_stock_detail(s)

        else:
            # ── Sector heatmap ─────────────────────────────────────────────
            st.markdown('<div class="section-hdr">Sector Heatmap — click ⤵ to drill in</div>', unsafe_allow_html=True)

            view = st.radio("View", ["Grid", "Treemap"], horizontal=True, label_visibility="collapsed")
            if view == "Treemap":
                fig = render_heatmap_plotly(sectors)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
                st.caption("Treemap area = stock count. Click on grid view to drill into a sector.")
            else:
                render_heatmap_grid(sectors)

            # ── Sector summary table ───────────────────────────────────────
            st.markdown('<hr class="pulse-divider"/>', unsafe_allow_html=True)
            st.markdown('<div class="section-hdr">Sector Summary — click a row to drill in</div>', unsafe_allow_html=True)

            df = render_sector_table(sectors)
            sel = st.dataframe(
                df, use_container_width=True, hide_index=True,
                on_select="rerun", selection_mode="single-row",
                column_config={
                    "Change%":  st.column_config.NumberColumn(format="%.2f%%"),
                    "RSI":      st.column_config.NumberColumn(format="%.1f"),
                    "Momentum": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
                    "Breadth%": st.column_config.NumberColumn(format="%.0f%%"),
                    "VolRatio": st.column_config.NumberColumn(format="%.2f×"),
                    "Stocks":   st.column_config.NumberColumn(format="%d"),
                }
            )
            if sel.selection.rows:
                st.session_state["selected_sector"] = sectors[sel.selection.rows[0]]["name"]
                st.rerun()

    # ═══════════════════════════════════════════════════════════════════════════
    # RRG TAB
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_rrg:
        st.markdown(
            '<div style="color:#8b949e;font-size:0.8rem;margin-bottom:8px">'
            'Clockwise rotation: <span style="color:#3b82f6">Improving</span> → '
            '<span style="color:#22c55e">Leading</span> → '
            '<span style="color:#eab308">Weakening</span> → '
            '<span style="color:#ef4444">Lagging</span>'
            '</div>', unsafe_allow_html=True)

        rrg_fig = render_rrg(sectors)
        clicked = st.plotly_chart(rrg_fig, use_container_width=True,
            on_select="rerun", selection_mode="points", config={"displayModeBar":False})

        if clicked and getattr(clicked, "selection", None) and clicked.selection.points:
            name = clicked.selection.points[0].get("text","").strip()
            if name:
                st.session_state["selected_sector"] = name
                st.session_state["_jump_overview"]   = True
                st.rerun()

        # Quadrant scorecards
        st.markdown('<hr class="pulse-divider"/>', unsafe_allow_html=True)
        qcols = st.columns(4)
        for col, (q, c, desc) in zip(qcols, [
            ("Leading",   "#22c55e","High RS · High Momentum"),
            ("Improving", "#3b82f6","Low RS · Rising Momentum"),
            ("Weakening", "#eab308","High RS · Falling Momentum"),
            ("Lagging",   "#ef4444","Low RS · Low Momentum"),
        ]):
            names = [s["name"] for s in sectors if s.get("rrg_quadrant") == q]
            col.markdown(
                f'<div style="background:#0d1117;border:1px solid #21262d;border-top:3px solid {c};'
                f'border-radius:0 0 8px 8px;padding:12px;text-align:center">'
                f'<div style="color:{c};font-weight:700;font-size:0.85rem">{q}</div>'
                f'<div style="color:#8b949e;font-size:0.68rem;margin:3px 0 8px">{desc}</div>'
                f'<div style="color:{c};font-size:1.6rem;font-weight:800">{len(names)}</div>'
                f'<div style="color:#8b949e;font-size:0.7rem;margin-top:4px">'
                f'{"  ·  ".join(names) if names else "—"}</div>'
                f'</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # SCREENER TAB
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_sc:
        # ── Sidebar-style filters ──────────────────────────────────────────
        with st.expander("⚙  Filters", expanded=False):
            fc1, fc2, fc3, fc4 = st.columns(4)
            with fc1:
                rsi_min, rsi_max = st.slider("RSI Range", 0, 100, (30, 75))
                momentum_min     = st.slider("Min Momentum", 0, 100, 40, step=5)
            with fc2:
                pattern = st.selectbox("Pattern", ["all","nr7","nr4","vcp","pocketpivot","rsdiv"],
                    format_func=lambda x: {"all":"All","nr7":"NR7","nr4":"NR4",
                        "vcp":"VCP","pocketpivot":"Pocket Pivot","rsdiv":"RS Divergence"}[x])
                rrg_filter = st.selectbox("RRG Quadrant",
                    ["all","Leading","Improving","Weakening","Lagging"])
            with fc3:
                dma_filter = st.selectbox("DMA Filter",
                    ["all","above20","above50","above200","allAbove"],
                    format_func=lambda x: {"all":"All","above20":"Above 20 DMA",
                        "above50":"Above 50 DMA","above200":"Above 200 DMA","allAbove":"All DMAs"}[x])
                vol_breakout = st.checkbox("Volume Breakout >1.5×", False)
            with fc4:
                sort_by = st.selectbox("Sort By",
                    ["change_pct","momentum","rsi","vol_ratio","rs"],
                    format_func=lambda x: {"change_pct":"Change%","momentum":"Momentum",
                        "rsi":"RSI","vol_ratio":"Vol Ratio","rs":"Rel Strength"}[x])
                grade_filter = st.multiselect("Grade", ["A","B","C"], default=["A","B","C"])

        # Active filters display
        active = [f"RSI {rsi_min}–{rsi_max}"]
        if momentum_min > 0:   active.append(f"Mom ≥{momentum_min}")
        if pattern != "all":   active.append(pattern.upper())
        if rrg_filter != "all":active.append(rrg_filter)
        if dma_filter != "all":active.append(dma_filter)
        if vol_breakout:       active.append("Vol Breakout")
        st.markdown(" ".join(f'<span class="filter-active">{a}</span>' for a in active), unsafe_allow_html=True)

        # Run screener
        with st.spinner("Screening full Nifty universe…"):
            results = fetch_screener(
                rsi_min=rsi_min, rsi_max=rsi_max, momentum_min=momentum_min,
                volume_breakout=vol_breakout, pattern=pattern,
                rrg_quadrant=rrg_filter, dma_filter=dma_filter,
            )

        # Grade filter (client-side)
        if grade_filter:
            results = [r for r in results if r.get("grade","C") in grade_filter]

        # Sort
        results_sorted = sorted(results, key=lambda s: s.get(sort_by, 0) or 0, reverse=True)

        # Count header
        a_count = sum(1 for r in results_sorted if r.get("grade")=="A")
        b_count = sum(1 for r in results_sorted if r.get("grade")=="B")
        c_count = sum(1 for r in results_sorted if r.get("grade")=="C")
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:14px;margin:8px 0 10px">'
            f'<span style="color:#e6edf3;font-weight:700">{len(results_sorted)} stocks</span>'
            f'<span class="grade-A">A: {a_count}</span>'
            f'<span class="grade-B">B: {b_count}</span>'
            f'<span class="grade-C">C: {c_count}</span>'
            f'</div>', unsafe_allow_html=True)

        if results_sorted:
            rows = []
            for s in results_sorted:
                rows.append({
                    "Grade":   s.get("grade","—"),
                    "Symbol":  s["symbol"].replace(".NS",""),
                    "Name":    s["name"][:22],
                    "Sector":  s["sector"],
                    "Price":   s["price"],
                    "Chg%":    s["change_pct"],
                    "RSI":     s["rsi"] if not math.isnan(s.get("rsi", float("nan"))) else 0,
                    "Mom":     s["momentum"],
                    "VolR":    s["vol_ratio"],
                    "RS%":     s["rs"],
                    "RRG":     s["rrg_quadrant"],
                    "20D":     s["above20dma"],
                    "50D":     s["above50dma"],
                    "200D":    s["above200dma"],
                    "Signals": " ".join(filter(None,[
                        "NR7" if s["is_nr7"] else "",
                        "NR4" if s["is_nr4"] else "",
                        "VCP" if s["is_vcp"] else "",
                        "PP"  if s["is_pocket_pivot"] else "",
                        "RS↑" if s["is_rs_div"] else "",
                    ])) or "—",
                })

            df = pd.DataFrame(rows)
            sel = st.dataframe(
                df, use_container_width=True, hide_index=True,
                on_select="rerun", selection_mode="single-row",
                column_config={
                    "Grade":  st.column_config.TextColumn(width=55),
                    "Symbol": st.column_config.TextColumn(width=80),
                    "Price":  st.column_config.NumberColumn(format="₹%.2f"),
                    "Chg%":   st.column_config.NumberColumn(format="%.2f%%"),
                    "RSI":    st.column_config.NumberColumn(format="%.1f"),
                    "Mom":    st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
                    "VolR":   st.column_config.NumberColumn(format="%.2f×"),
                    "RS%":    st.column_config.NumberColumn(format="%+.1f%%"),
                    "20D":    st.column_config.CheckboxColumn(width=45),
                    "50D":    st.column_config.CheckboxColumn(width=45),
                    "200D":   st.column_config.CheckboxColumn(width=45),
                }
            )
            if sel.selection.rows:
                render_stock_detail(results_sorted[sel.selection.rows[0]])

        else:
            st.markdown(
                '<div style="text-align:center;padding:40px;color:#8b949e">'
                '<div style="font-size:2rem">🔍</div>'
                '<div style="font-weight:600;margin-top:8px">No stocks match</div>'
                '<div style="font-size:0.82rem;margin-top:4px">Try relaxing the RSI or momentum filters</div>'
                '</div>', unsafe_allow_html=True)

    # ── Footer ─────────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="text-align:center;padding:20px 0 8px;color:#30363d;font-size:0.68rem">'
        f'Pulse · Data: Yahoo Finance · Refresh #{st.session_state.refresh_count} · '
        f'Next in {max(0,int(AUTO_REFRESH_SECS - (time.time()-st.session_state.last_refresh)))}s'
        f'</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
