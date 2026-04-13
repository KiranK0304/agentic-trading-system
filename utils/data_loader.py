import time
import pandas as pd
import yfinance as yf
import nsepython

# Mapping common names to yfinance symbols for fallback
YF_SYMBOL_MAP = {
    "NIFTY 50": "^NSEI",
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
}

def get_live_info(symbol: str = "NIFTY 50") -> dict:
    """
    Fetch real-time snapshot data using nsepython, with a fallback
    to yfinance if the NSE API gets rate-limited/blocked.
    """
    print(f"Fetching live data for {symbol}...")
    
    # 1. Attempt NSE Python
    try:
        quote = nsepython.nse_quote(symbol)
        if quote and "lastPrice" in quote:
            print("✅ Successfully fetched live data from NSE.")
            return {
                "symbol": symbol,
                "ltp": quote.get("lastPrice", 0),
                "change": quote.get("change", 0),
                "pChange": quote.get("pChange", 0),
                "open": quote.get("open", 0),
                "high": quote.get("dayHigh", 0),
                "low": quote.get("dayLow", 0),
                "source": "nsepython"
            }
    except Exception as e:
        print(f"⚠️ nsepython failed ({type(e).__name__}): {e}. Falling back to yfinance...")

    # 2. Fallback to yfinance
    yf_symbol = YF_SYMBOL_MAP.get(symbol, f"{symbol}.NS")
    print(f"Using yfinance fallback ticker: {yf_symbol}")
    try:
        ticker = yf.Ticker(yf_symbol)
        data = ticker.fast_info
        last_price = data.last_price
        prev_close = data.previous_close
        change = last_price - prev_close
        p_change = (change / prev_close) * 100 if prev_close else 0
        
        print("✅ Successfully fetched live data from yfinance.")
        return {
            "symbol": symbol,
            "ltp": last_price,
            "change": round(change, 2),
            "pChange": round(p_change, 2),
            "open": data.open,
            "high": data.day_high,
            "low": data.day_low,
            "source": "yfinance"
        }
    except Exception as e:
        print(f"❌ Both NSE and yfinance failed to fetch live data: {e}")
        return {}


def get_historical_data(
    symbol: str = "NIFTY 50",
    period: str = "5d",
    interval: str = "5m",
    max_retries: int = 3,
) -> pd.DataFrame:
    """
    Fetch historical intraday 5-minute candles.
    Uses yfinance reliably for exact Pandas OHLCV structure.
    """
    valid_intervals = ["1m", "2m", "5m", "15m", "30m", "60m"]
    if interval not in valid_intervals:
        print(f"⚠️ Warning: Interval '{interval}' not standard. Using '5m'.")
        interval = "5m"

    yf_symbol = YF_SYMBOL_MAP.get(symbol, f"{symbol}.NS")
    print(f"Fetching {interval} historical data for {symbol} (Mapped to {yf_symbol})...")

    df = pd.DataFrame()

    for attempt in range(max_retries):
        try:
            df = yf.download(
                tickers=yf_symbol,
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
        print(f"❌ Failed to fetch historical data for {symbol} after {max_retries} attempts.")
        return pd.DataFrame()

    # Clean up structure to match expected node inputs
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

    # If yfinance returned MultiIndex columns, flatten them.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

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
    live = get_live_info("NIFTY 50")
    print("\nLive Info:", live)
    
    df = get_historical_data("NIFTY 50", period="1d", interval="5m")
    if not df.empty:
        print("\nHistorical Data last 5 rows:")
        print(df.tail(5)[["Symbol", "Time", "Close", "Volume"]])
