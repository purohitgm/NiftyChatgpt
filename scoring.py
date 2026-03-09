def momentum(df):
    score = 0
    if df.Close.iloc[-1] > df.EMA20.iloc[-1]:
        score += 20
    if df.Close.iloc[-1] > df.EMA50.iloc[-1]:
        score += 20
    if df.Close.iloc[-1] > df.EMA200.iloc[-1]:
        score += 20
    if df.RSI.iloc[-1] > 60:
        score += 20
    if df.Volume.iloc[-1] > df.VOL20.iloc[-1]:
        score += 20
    return score