"""
Pulse — Nifty Sector Analytics Dashboard
Streamlit port of the Next.js/React v0 dashboard.

Run:  streamlit run pulse_dashboard.py
"""

import math
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from data_fetcher import (
    fetch_chart, fetch_all_sectors, fetch_indices,
    fetch_sector_data, fetch_screener,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pulse · Nifty Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Dark terminal feel */
[data-testid="stAppViewContainer"] { background: #0d1117; }
[data-testid="stHeader"] { background: #0d1117; }
.block-container { padding-top: 1rem; }
div[data-testid="metric-container"] { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px; }
div[data-testid="metric-container"] label { color: #8b949e !important; font-size: 0.75rem !important; }
div[data-testid="metric-container"] [data-testid="metric-value"] { color: #e6edf3 !important; font-size: 1.1rem !important; }

.heatmap-cell {
    padding: 12px; border-radius: 8px; cursor: pointer;
    display: flex; flex-direction: column; gap: 4px;
    transition: transform .15s;
}
.heatmap-cell:hover { transform: scale(1.03); }

.grade-A { background: #1a4731; color: #4ade80; border: 1px solid #166534; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 0.8rem; }
.grade-B { background: #422006; color: #fb923c; border: 1px solid #7c2d12; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 0.8rem; }
.grade-C { background: #1e1e2e; color: #94a3b8; border: 1px solid #334155; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 0.8rem; }

.signal-badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 0.72rem; font-weight: 600; margin: 2px;
}
.sig-nr7    { background: #422006; color: #fb923c; }
.sig-nr4    { background: #7c2d12; color: #fca5a5; }
.sig-vcp    { background: #2e1065; color: #c084fc; }
.sig-pp     { background: #14532d; color: #86efac; }
.sig-rsdiv  { background: #0c4a6e; color: #7dd3fc; }

hr { border-color: #30363d; }
</style>
""", unsafe_allow_html=True)


# ── Helper utils ───────────────────────────────────────────────────────────────

def fmt_pct(v: float) -> str:
    return f"+{v:.2f}%" if v >= 0 else f"{v:.2f}%"

def fmt_inr(v: float) -> str:
    return f"₹{v:,.2f}"

def rsi_color(rsi: float) -> str:
    if math.isnan(rsi): return "#8b949e"
    if rsi >= 70: return "#f59e0b"
    if rsi <= 30: return "#60a5fa"
    return "#e6edf3"

def change_color(v: float) -> str:
    return "#4ade80" if v >= 0 else "#f87171"

def rrg_color(q: str) -> str:
    return {"Leading": "#22c55e", "Weakening": "#eab308", "Lagging": "#ef4444", "Improving": "#3b82f6"}.get(q, "#8b949e")

def heatmap_bg(change: float) -> str:
    if change >= 2:    return "#065f46"
    if change >= 1:    return "#047857"
    if change >= 0.5:  return "#059669"
    if change >= 0:    return "#0d2b1f"
    if change >= -0.5: return "#2d0f0f"
    if change >= -1:   return "#7f1d1d"
    if change >= -2:   return "#991b1b"
    return "#b91c1c"


# ── Candlestick chart ──────────────────────────────────────────────────────────

def render_candlestick(ohlcv: list, symbol: str, nr7_marks: list = None, nr4_marks: list = None) -> go.Figure:
    df = pd.DataFrame(ohlcv)
    if df.empty:
        return go.Figure()
    df["date"] = pd.to_datetime(df["date"])

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.75, 0.25], vertical_spacing=0.02)

    # Candles
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"],
        name=symbol.replace(".NS", ""),
        increasing_line_color="#4ade80", decreasing_line_color="#f87171",
        increasing_fillcolor="#4ade80", decreasing_fillcolor="#f87171",
    ), row=1, col=1)

    # NR7 markers
    if nr7_marks:
        nr7_df = df[df["date"].isin([pd.Timestamp(d) for d in nr7_marks])]
        if not nr7_df.empty:
            fig.add_trace(go.Scatter(
                x=nr7_df["date"], y=nr7_df["low"] * 0.997,
                mode="markers", marker=dict(symbol="triangle-up", size=9, color="#f59e0b"),
                name="NR7",
            ), row=1, col=1)

    # NR4 markers
    if nr4_marks:
        nr4_df = df[df["date"].isin([pd.Timestamp(d) for d in nr4_marks])]
        if not nr4_df.empty:
            fig.add_trace(go.Scatter(
                x=nr4_df["date"], y=nr4_df["low"] * 0.994,
                mode="markers", marker=dict(symbol="triangle-up", size=7, color="#f97316"),
                name="NR4",
            ), row=1, col=1)

    # Volume
    colors = ["#4ade80" if c >= o else "#f87171" for c, o in zip(df["close"], df["open"])]
    fig.add_trace(go.Bar(
        x=df["date"], y=df["volume"], name="Volume",
        marker_color=colors, opacity=0.7,
    ), row=2, col=1)

    fig.update_layout(
        paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
        font=dict(color="#e6edf3", size=11),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.05, bgcolor="rgba(0,0,0,0)"),
        height=420,
    )
    fig.update_xaxes(gridcolor="#30363d", showgrid=True)
    fig.update_yaxes(gridcolor="#30363d", showgrid=True)
    return fig


# ── RRG Chart ──────────────────────────────────────────────────────────────────

def render_rrg(sectors: list) -> go.Figure:
    fig = go.Figure()

    # Quadrant shading
    for x_range, y_range, color, label in [
        ([100, 115], [100, 115], "rgba(34,197,94,0.06)",  "Leading"),
        ([100, 115], [85, 100],  "rgba(234,179,8,0.06)",  "Weakening"),
        ([85, 100],  [85, 100],  "rgba(239,68,68,0.06)",  "Lagging"),
        ([85, 100],  [100, 115], "rgba(59,130,246,0.06)", "Improving"),
    ]:
        fig.add_shape(type="rect",
            x0=x_range[0], x1=x_range[1], y0=y_range[0], y1=y_range[1],
            fillcolor=color, line=dict(width=0), layer="below")

    for s in sectors:
        q     = s.get("rrg_quadrant", "Lagging")
        color = rrg_color(q)
        rs_r  = s.get("rs_ratio", 100)
        rs_m  = s.get("rs_momentum", 100)

        # Dot + label
        fig.add_trace(go.Scatter(
            x=[rs_r], y=[rs_m],
            mode="markers+text",
            marker=dict(size=14, color=color, line=dict(width=2, color="#0d1117")),
            text=[s["name"]],
            textposition="middle right",
            textfont=dict(size=11, color="#e6edf3"),
            name=s["name"],
            hovertemplate=(
                f"<b>{s['name']}</b><br>"
                f"RS-Ratio: {rs_r:.2f}<br>"
                f"RS-Momentum: {rs_m:.2f}<br>"
                f"Quadrant: {q}<extra></extra>"
            ),
            customdata=[s["name"]],
        ))

    # Reference lines
    fig.add_hline(y=100, line=dict(color="#30363d", dash="dash", width=1))
    fig.add_vline(x=100, line=dict(color="#30363d", dash="dash", width=1))

    # Quadrant labels
    for x, y, label, color in [
        (87, 113, "IMPROVING", "#60a5fa"),
        (113, 113, "LEADING",  "#4ade80"),
        (113, 87,  "WEAKENING","#f59e0b"),
        (87, 87,   "LAGGING",  "#f87171"),
    ]:
        fig.add_annotation(x=x, y=y, text=label, showarrow=False,
            font=dict(size=9, color=color), opacity=0.5)

    fig.update_layout(
        paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
        font=dict(color="#e6edf3"),
        xaxis=dict(title="← Lagging   RS-Ratio   Leading →", gridcolor="#30363d", range=[85, 115]),
        yaxis=dict(title="RS-Momentum", gridcolor="#30363d", range=[85, 115]),
        showlegend=False,
        height=520,
        margin=dict(l=60, r=20, t=20, b=60),
    )
    return fig


# ── Sector heatmap ─────────────────────────────────────────────────────────────

def render_heatmap(sectors: list, selected: str = None):
    cols = st.columns(5)
    for i, s in enumerate(sectors):
        bg   = heatmap_bg(s["change"])
        border = "2px solid #fff" if s["name"] == selected else "1px solid transparent"
        q_color = rrg_color(s.get("rrg_quadrant", "Lagging"))

        with cols[i % 5]:
            st.markdown(f"""
            <div class="heatmap-cell" style="background:{bg}; border:{border}">
                <span style="font-weight:700; color:#fff; font-size:0.85rem;">{s['name']}</span>
                <span style="font-size:1.2rem; font-weight:800; color:#fff;">{fmt_pct(s['change'])}</span>
                <div style="display:flex; gap:12px; margin-top:4px;">
                    <span style="font-size:0.7rem; color:rgba(255,255,255,0.7);">RSI <b style="color:#fff">{s['rsi']:.0f}</b></span>
                    <span style="font-size:0.7rem; color:rgba(255,255,255,0.7);">Breadth <b style="color:#fff">{s['breadth']:.0f}%</b></span>
                </div>
                <span style="font-size:0.7rem; padding:2px 6px; background:rgba(0,0,0,0.3); color:{q_color}; border-radius:3px; width:fit-content; margin-top:2px;">{s.get('rrg_quadrant','')}</span>
            </div>
            """, unsafe_allow_html=True)
            if st.button("▶ Drill", key=f"drill_{s['name']}", use_container_width=True):
                st.session_state["selected_sector"] = s["name"]
                st.rerun()


# ── Market overview bar ────────────────────────────────────────────────────────

def render_market_overview(indices: list):
    # Show first 5 key indices as metrics
    display = [i for i in indices if i["name"] in ("NIFTY 50", "NIFTY BANK", "NIFTY IT", "NIFTY PHARMA", "NIFTY AUTO")]
    if not display:
        display = indices[:5]

    cols = st.columns(len(display))
    for col, idx in zip(cols, display):
        delta_str = f"{fmt_pct(idx['change_pct'])}  RSI {idx['rsi']:.0f}" if not math.isnan(idx.get("rsi", float("nan"))) else fmt_pct(idx['change_pct'])
        col.metric(
            label=idx["name"],
            value=f"{idx['price']:,.0f}",
            delta=delta_str,
        )


# ── Stock detail expander ──────────────────────────────────────────────────────

def render_stock_detail(stock: dict):
    with st.expander(f"📊 {stock['symbol'].replace('.NS','')} — {stock['name']}", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Price", fmt_inr(stock["price"]), fmt_pct(stock["change_pct"]))
        c2.metric("RSI (14)", f"{stock['rsi']:.1f}")
        c3.metric("Momentum", f"{stock['momentum']:.0f}/100")
        c4.metric("Vol Ratio", f"{stock['vol_ratio']:.2f}×")

        # Signal badges
        badges = []
        if stock["is_nr7"]:        badges.append('<span class="signal-badge sig-nr7">NR7</span>')
        if stock["is_nr4"]:        badges.append('<span class="signal-badge sig-nr4">NR4</span>')
        if stock["is_vcp"]:        badges.append('<span class="signal-badge sig-vcp">VCP</span>')
        if stock["is_pocket_pivot"]:badges.append('<span class="signal-badge sig-pp">Pocket Pivot</span>')
        if stock["is_rs_div"]:     badges.append('<span class="signal-badge sig-rsdiv">RS Divergence</span>')
        if badges:
            st.markdown(" ".join(badges), unsafe_allow_html=True)

        ca, cb = st.columns(2)
        with ca:
            st.markdown("**Moving Averages**")
            ma_df = pd.DataFrame([{
                "MA":    ["20 DMA", "50 DMA", "200 DMA"],
                "Value": [f"{stock['dma20']:.2f}", f"{stock['dma50']:.2f}", f"{stock['dma200']:.2f}"],
                "Status":[
                    "✅ Above" if stock["above20dma"]  else "❌ Below",
                    "✅ Above" if stock["above50dma"]  else "❌ Below",
                    "✅ Above" if stock["above200dma"] else "❌ Below",
                ],
            }])
            st.dataframe(ma_df, hide_index=True, use_container_width=True)

        with cb:
            st.markdown("**EMA Values**")
            ema_df = pd.DataFrame([{
                "EMA": ["EMA 5", "EMA 10", "EMA 21", "EMA 50"],
                "Value": [f"{stock['ema5']:.2f}", f"{stock['ema10']:.2f}", f"{stock['ema21']:.2f}", f"{stock['ema50']:.2f}"],
            }])
            st.dataframe(ema_df, hide_index=True, use_container_width=True)

        # 52-week range
        lo, hi, price = stock["low52w"], stock["high52w"], stock["price"]
        pct_in_range = (price - lo) / (hi - lo) * 100 if hi > lo else 50
        st.markdown(f"**52-Week Range** — {fmt_inr(lo)} ↔ {fmt_inr(hi)}")
        st.progress(int(max(0, min(100, pct_in_range))))

        # Candlestick
        if stock.get("ohlcv"):
            from technical_indicators import detect_nr7, detect_nr4
            ohlcv = stock["ohlcv"]
            nr7_dates = [ohlcv[i]["date"] for i, v in enumerate(detect_nr7(ohlcv)) if v]
            nr4_dates = [ohlcv[i]["date"] for i, v in enumerate(detect_nr4(ohlcv)) if v]
            st.plotly_chart(
                render_candlestick(ohlcv, stock["symbol"], nr7_dates, nr4_dates),
                use_container_width=True
            )

        st.markdown(
            f"[🔗 Screener.in](https://www.screener.in/company/{stock['symbol'].replace('.NS','')}/) &nbsp;|&nbsp; "
            f"[📈 TradingView](https://in.tradingview.com/chart/?symbol=NSE:{stock['symbol'].replace('.NS','')})"
        )


# ── Main Dashboard ─────────────────────────────────────────────────────────────

def main():
    # Session state
    if "selected_sector" not in st.session_state:
        st.session_state["selected_sector"] = None

    # Header
    col_logo, col_title, col_refresh = st.columns([0.5, 8, 1.5])
    with col_logo:
        st.markdown("### 📈")
    with col_title:
        st.markdown("## Pulse &nbsp; <span style='font-size:0.9rem; color:#8b949e'>Nifty Sector Analytics</span>", unsafe_allow_html=True)
    with col_refresh:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown("<hr style='margin:0 0 12px'/>", unsafe_allow_html=True)

    # Load data
    with st.spinner("Loading market data…"):
        indices = fetch_indices()
        sectors = fetch_all_sectors()

    # Market overview
    if indices:
        render_market_overview(indices)
        st.markdown("")

    # Tabs
    tab_overview, tab_rrg, tab_screener = st.tabs(["🗺 Sector Overview", "🔄 RRG Chart", "🔍 Screener"])

    # ── OVERVIEW TAB ──────────────────────────────────────────────────────────
    with tab_overview:
        selected = st.session_state["selected_sector"]

        if selected:
            if st.button("← Back to all sectors"):
                st.session_state["selected_sector"] = None
                st.rerun()

            with st.spinner(f"Loading {selected}…"):
                detail = fetch_sector_data(selected)

            if detail:
                st.subheader(f"{selected} Sector")
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Change",    fmt_pct(detail["change"]))
                m2.metric("RSI",       f"{detail['rsi']:.1f}")
                m3.metric("Momentum",  f"{detail['momentum']:.0f}")
                m4.metric("Breadth",   f"{detail['breadth']:.0f}%")
                m5.metric("Vol Ratio", f"{detail['vol_ratio']:.2f}×")

                st.markdown("---")

                # Stock table for this sector
                if detail["stocks"]:
                    stock_rows = []
                    for s in detail["stocks"]:
                        patterns = " ".join(filter(None, [
                            "NR7" if s["is_nr7"] else "",
                            "NR4" if s["is_nr4"] else "",
                            "VCP" if s["is_vcp"] else "",
                            "PP"  if s["is_pocket_pivot"] else "",
                            "RS↑" if s["is_rs_div"] else "",
                        ]))
                        stock_rows.append({
                            "Symbol": s["symbol"].replace(".NS", ""),
                            "Name":   s["name"],
                            "Price":  f"{s['price']:,.2f}",
                            "Chg%":   fmt_pct(s["change_pct"]),
                            "RSI":    f"{s['rsi']:.1f}",
                            "Mom":    f"{s['momentum']:.0f}",
                            "VolR":   f"{s['vol_ratio']:.2f}×",
                            "RRG":    s["rrg_quadrant"],
                            "Signals": patterns or "—",
                        })
                    df = pd.DataFrame(stock_rows)
                    sel = st.dataframe(
                        df, use_container_width=True, hide_index=True,
                        on_select="rerun", selection_mode="single-row"
                    )
                    if sel.selection.rows:
                        chosen = detail["stocks"][sel.selection.rows[0]]
                        render_stock_detail(chosen)

        else:
            # Heatmap
            st.markdown("#### Sector Heatmap")
            render_heatmap(sectors)

            # Summary table
            st.markdown("---")
            st.markdown("#### Sector Summary")
            rows = []
            for s in sectors:
                rows.append({
                    "Sector":   s["name"],
                    "Change%":  fmt_pct(s["change"]),
                    "RSI":      f"{s['rsi']:.1f}",
                    "Momentum": f"{s['momentum']:.0f}",
                    "Breadth":  f"{s['breadth']:.0f}%",
                    "Vol Ratio":f"{s['vol_ratio']:.2f}×",
                    "RRG":      s.get("rrg_quadrant", "—"),
                    "Stocks":   s["stock_count"],
                })
            df = pd.DataFrame(rows)
            sel = st.dataframe(
                df, use_container_width=True, hide_index=True,
                on_select="rerun", selection_mode="single-row"
            )
            if sel.selection.rows:
                chosen_name = sectors[sel.selection.rows[0]]["name"]
                st.session_state["selected_sector"] = chosen_name
                st.rerun()

    # ── RRG TAB ───────────────────────────────────────────────────────────────
    with tab_rrg:
        st.markdown("#### Relative Rotation Graph — Sectors vs Nifty 50")
        st.markdown(
            "<span style='color:#8b949e; font-size:0.85rem'>"
            "Click a sector dot to drill into it. Clockwise rotation: Improving → Leading → Weakening → Lagging."
            "</span>", unsafe_allow_html=True
        )
        rrg_fig = render_rrg(sectors)
        clicked = st.plotly_chart(rrg_fig, use_container_width=True, on_select="rerun", selection_mode="points")

        if clicked and clicked.selection and clicked.selection.points:
            pt_name = clicked.selection.points[0].get("text") or clicked.selection.points[0].get("customdata")
            if pt_name:
                name = pt_name[0] if isinstance(pt_name, list) else pt_name
                st.session_state["selected_sector"] = name
                st.rerun()

        # RRG summary legend
        leg_cols = st.columns(4)
        for col, (q, color, desc) in zip(leg_cols, [
            ("Leading",   "#22c55e", "High RS · High Momentum"),
            ("Weakening", "#eab308", "High RS · Falling Momentum"),
            ("Lagging",   "#ef4444", "Low RS · Low Momentum"),
            ("Improving", "#3b82f6", "Low RS · Rising Momentum"),
        ]):
            n = sum(1 for s in sectors if s.get("rrg_quadrant") == q)
            col.markdown(
                f"<div style='background:#161b22; border:1px solid #30363d; border-radius:6px; padding:10px; text-align:center'>"
                f"<div style='color:{color}; font-weight:700; font-size:0.9rem'>{q}</div>"
                f"<div style='color:#8b949e; font-size:0.75rem'>{desc}</div>"
                f"<div style='color:{color}; font-size:1.4rem; font-weight:800'>{n}</div>"
                f"</div>", unsafe_allow_html=True
            )

    # ── SCREENER TAB ──────────────────────────────────────────────────────────
    with tab_screener:
        st.markdown("#### Stock Screener — Full Nifty Universe")

        # Filter controls
        with st.expander("🔧 Filters", expanded=False):
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                rsi_min, rsi_max = st.slider("RSI Range", 0, 100, (0, 100), step=1)
                momentum_min     = st.slider("Min Momentum Score", 0, 100, 0, step=5)
            with fc2:
                pattern = st.selectbox("Pattern Filter", [
                    "all", "nr7", "nr4", "vcp", "pocketpivot", "rsdiv"
                ], format_func=lambda x: {
                    "all": "All Patterns", "nr7": "NR7",
                    "nr4": "NR4", "vcp": "VCP",
                    "pocketpivot": "Pocket Pivot", "rsdiv": "RS Divergence"
                }[x])
                rrg_filter = st.selectbox("RRG Quadrant", ["all", "Leading", "Improving", "Weakening", "Lagging"])
            with fc3:
                dma_filter = st.selectbox("DMA Filter", [
                    "all", "above20", "above50", "above200", "allAbove"
                ], format_func=lambda x: {
                    "all": "All", "above20": "Above 20 DMA",
                    "above50": "Above 50 DMA", "above200": "Above 200 DMA",
                    "allAbove": "Above All DMAs"
                }[x])
                vol_breakout = st.checkbox("Volume Breakout (>1.5×)", value=False)

        # Run screener
        with st.spinner("Screening full universe…"):
            results = fetch_screener(
                rsi_min=rsi_min, rsi_max=rsi_max,
                momentum_min=momentum_min,
                volume_breakout=vol_breakout,
                pattern=pattern,
                rrg_quadrant=rrg_filter,
                dma_filter=dma_filter,
            )

        st.markdown(f"**{len(results)} stocks match** your filters")

        if results:
            # Sort options
            sort_col = st.selectbox("Sort by", ["change_pct", "momentum", "rsi", "vol_ratio", "rs"], key="sort_col",
                format_func=lambda x: {"change_pct":"Change%","momentum":"Momentum","rsi":"RSI","vol_ratio":"Vol Ratio","rs":"Rel. Strength"}[x])
            results_sorted = sorted(results, key=lambda s: s.get(sort_col, 0) or 0, reverse=True)

            # Build display DF
            rows = []
            for s in results_sorted:
                patterns = " ".join(filter(None, [
                    "NR7" if s["is_nr7"] else "",
                    "NR4" if s["is_nr4"] else "",
                    "VCP" if s["is_vcp"] else "",
                    "PP"  if s["is_pocket_pivot"] else "",
                    "RS↑" if s["is_rs_div"] else "",
                ]))
                rows.append({
                    "Grade":   s.get("grade", "—"),
                    "Symbol":  s["symbol"].replace(".NS", ""),
                    "Name":    s["name"],
                    "Sector":  s["sector"],
                    "Price":   f"{s['price']:,.2f}",
                    "Chg%":    fmt_pct(s["change_pct"]),
                    "RSI":     f"{s['rsi']:.1f}" if not math.isnan(s.get("rsi", float("nan"))) else "—",
                    "Mom":     f"{s['momentum']:.0f}",
                    "VolR":    f"{s['vol_ratio']:.2f}×",
                    "RS":      f"{s['rs']:+.1f}%",
                    "RRG":     s["rrg_quadrant"],
                    "Signals": patterns or "—",
                    "20D":     "✅" if s["above20dma"]  else "❌",
                    "50D":     "✅" if s["above50dma"]  else "❌",
                    "200D":    "✅" if s["above200dma"] else "❌",
                })

            df = pd.DataFrame(rows)
            sel = st.dataframe(
                df, use_container_width=True, hide_index=True,
                on_select="rerun", selection_mode="single-row"
            )
            if sel.selection.rows:
                chosen = results_sorted[sel.selection.rows[0]]
                render_stock_detail(chosen)

        else:
            st.info("No stocks match the current filters. Try relaxing the criteria.")


if __name__ == "__main__":
    main()
