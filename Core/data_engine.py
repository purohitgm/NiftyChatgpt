import yfinance as yf

def load_market_data(tickers):
    data = yf.download(
        tickers,
        period="1y",
        interval="1d",
        group_by="ticker",
        threads=True
    )
    return data