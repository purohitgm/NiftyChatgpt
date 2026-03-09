def nr7(df):
    r = df["High"] - df["Low"]
    df["NR7"] = r == r.rolling(7).min()
    return df

def vcp(df):
    contraction = df["High"].rolling(10).max() - df["Low"].rolling(10).min()
    df["VCP"] = contraction < contraction.rolling(30).mean()
    return df

def pocket_pivot(df):
    df["PP"] = (
        (df["Volume"] > df["Volume"].rolling(10).max())
        & (df["Close"] > df["EMA20"])
    )
    return df