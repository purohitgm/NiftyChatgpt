import streamlit as st
import pandas as pd

from config import NIFTY50
from core.data_engine import load_market_data
from core.indicators import indicators
from core.patterns import nr7
from core.scoring import momentum
from ui.heatmaps import sector_heatmap
from ui.screener import screener

st.set_page_config(layout="wide")
st.title("Pro Nifty Terminal")

data = load_market_data(NIFTY50)

rows = []

for t in NIFTY50:
    try:
        df = data[t].dropna()
        df = indicators(df)
        df = nr7(df)

        m = momentum(df)

        rows.append({
            "Stock": t,
            "RSI": df.RSI.iloc[-1],
            "Momentum": m,
            "NR7": df.NR7.iloc[-1]
        })
    except:
        pass

table = pd.DataFrame(rows)

st.subheader("Stock Screener")
screener(table)

st.subheader("Momentum Heatmap")
fig = sector_heatmap(table)
st.plotly_chart(fig, use_container_width=True)