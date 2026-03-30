import yfinance as yf
import pandas as pd
from datetime import datetime
import time

def fetch_data(symbol, period="5d", interval="5m", max_retries=3):
    """
    Fetch 5-minute OHLCV data and return as pandas DataFrame.
    """
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
                repair=True
            )
            
            if not df.empty:
                break
                
            print(f"Attempt {attempt+1}: Empty data. Retrying...")
            time.sleep(5)
            
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(8)
            else:
                raise

    if df.empty:
        print(f"❌ No data returned for {symbol}")
        return pd.DataFrame()

    # Clean and prepare
    df = df.dropna(how='all')
    
    # Timezone handling (Asia/Kolkata for NSE)
    if df.index.tz is None:
        df.index = df.index.tz_localize('Asia/Kolkata')
    else:
        df.index = df.index.tz_convert('Asia/Kolkata')

    # Add columns
    df = df.copy()
    df['Symbol'] = symbol
    df['Date'] = df.index.date
    df['Time'] = df.index.time
    df['Datetime_IST'] = df.index

    # Reorder columns
    columns_order = ['Symbol', 'Date', 'Time', 'Open', 'High', 'Low', 'Close', 'Volume']
    df = df[columns_order]

    print(f"✅ Fetched {len(df)} rows for {symbol} | {df.index.min()} to {df.index.max()}")
    return df

