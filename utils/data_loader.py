import time

import pandas as pd
import yfinance as yf


def fetch_data(
    symbol: str,
    period: str = "5d",
    interval: str = "5m",
    max_retries: int = 3,
) -> pd.DataFrame:
    """
    Fetch 5-minute (or specified interval) OHLCV data for NSE stocks/index.
    Returns a clean pandas DataFrame.
    """
    valid_intervals = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"]
    if interval not in valid_intervals:
        print(f"⚠️ Warning: Interval '{interval}' not standard. Using '5m'.")
        interval = "5m"

    print(f"Fetching {interval} data for {symbol} (period={period})...")

    df = pd.DataFrame()

    for attempt in range(max_retries):
        try:
            df = yf.download(
                tickers=symbol,
                period=period,
                interval=interval,
                auto_adjust=True,
                prepost=False,
                progress=False,
                timeout=30,
                repair=True,
            )

            if not df.empty:
                break

            print(f"Attempt {attempt + 1}: Empty DataFrame. Retrying...")
            time.sleep(6)

        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {type(e).__name__} - {e}")
            if attempt < max_retries - 1:
                time.sleep(10)
            else:
                raise

    if df.empty:
        print(f"❌ Failed to fetch data for {symbol} after {max_retries} attempts.")
        return pd.DataFrame()

    df = df.dropna(how="all")

    if df.index.tz is None:
        df.index = df.index.tz_localize("Asia/Kolkata")
    else:
        df.index = df.index.tz_convert("Asia/Kolkata")

    df = df.copy()
    df["Symbol"] = symbol
    df["Date"] = df.index.date
    df["Time"] = df.index.time
    df["Datetime_IST"] = df.index

    columns_order = [
        "Symbol",
        "Date",
        "Time",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
        "Datetime_IST",
    ]
    df = df[columns_order]
    latest_close = float(df["Close"].iloc[-1])

    print(f"✅ Successfully fetched {len(df)} rows for {symbol}")
    print(f"   Time range : {df['Datetime_IST'].iloc[0]} → {df['Datetime_IST'].iloc[-1]}")
    print(f"   Latest Close: ₹{latest_close:.2f}\n")
    return df


if __name__ == "__main__":
    df = fetch_data("HDFCBANK.NS", period="5d", interval="5m")

    if not df.empty:
        print("Last 5 rows preview:")
        print(df.tail(5)[["Symbol", "Date", "Time", "Close", "Volume"]])

        print(f"\nDataFrame shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
