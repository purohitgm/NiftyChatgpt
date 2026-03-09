import ta

def indicators(df):
    df["RSI"] = ta.momentum.RSIIndicator(df["Close"],14).rsi()
    df["EMA20"] = df["Close"].ewm(span=20).mean()
    df["EMA50"] = df["Close"].ewm(span=50).mean()
    df["EMA200"] = df["Close"].ewm(span=200).mean()
    df["VOL20"] = df["Volume"].rolling(20).mean()
    return df