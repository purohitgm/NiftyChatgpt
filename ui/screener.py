import streamlit as st

def screener(df):
    rsi = st.slider("RSI Range",0,100,(40,80))
    momentum = st.slider("Momentum Threshold",0,100,50)

    result = df[
        (df.RSI.between(*rsi)) &
        (df.Momentum > momentum)
    ]

    st.dataframe(result)