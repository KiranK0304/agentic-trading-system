import pandas as pd
import ta

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add key technical indicators to the DataFrame using the `ta` library."""
    df = df.copy()
    
    if len(df) < 50:
        return df
        
    # 1. Moving Averages
    df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
    df['EMA_9'] = ta.trend.ema_indicator(df['Close'], window=9)
    df['EMA_20'] = ta.trend.ema_indicator(df['Close'], window=20)
    df['EMA_50'] = ta.trend.ema_indicator(df['Close'], window=50)
    
    # 2. MACD
    macd = ta.trend.MACD(close=df['Close'])
    df['MACD_Line'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Hist'] = macd.macd_diff()
    
    # 3. Bollinger Bands
    bb = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)
    df['BB_Upper'] = bb.bollinger_hband()
    df['BB_Lower'] = bb.bollinger_lband()
    df['BB_Mid'] = bb.bollinger_mavg()
    
    # 4. RSI
    df['RSI_14'] = ta.momentum.rsi(close=df['Close'], window=14)
    
    # 5. VWAP
    vwap = ta.volume.VolumeWeightedAveragePrice(
        high=df['High'], 
        low=df['Low'], 
        close=df['Close'], 
        volume=df['Volume'], 
        window=14
    )
    df['VWAP'] = vwap.volume_weighted_average_price()
    
    # Fill NAs carefully or let the LLM see NaNs for very early data
    return df

def generate_technical_summary(df: pd.DataFrame) -> str:
    """Generate a text summary of the latest technical indicators."""
    if len(df) < 50:
        return "Not enough data for stable technical indicators."
        
    df_ta = add_technical_indicators(df)
    latest = df_ta.iloc[-1]
    prev = df_ta.iloc[-2]
    
    # Safely get MACD info
    macd_signal_cross = ""
    if pd.notna(prev['MACD_Line']) and pd.notna(prev['MACD_Signal']):
        if prev['MACD_Line'] <= prev['MACD_Signal'] and latest['MACD_Line'] > latest['MACD_Signal']:
            macd_signal_cross = " [BULLISH CROSS]"
        elif prev['MACD_Line'] >= prev['MACD_Signal'] and latest['MACD_Line'] < latest['MACD_Signal']:
            macd_signal_cross = " [BEARISH CROSS]"

    summary = f"""--- TECHNICAL INDICATORS SNAPSHOT ---
RSI (14)    : {latest['RSI_14']:.2f}
MACD        : Line {latest['MACD_Line']:.2f} | Signal {latest['MACD_Signal']:.2f} | Hist {latest['MACD_Hist']:.2f}{macd_signal_cross}
Trend EMAs  : EMA(9) = {latest['EMA_9']:.2f} | EMA(20) = {latest['EMA_20']:.2f} | EMA(50) = {latest['EMA_50']:.2f}
Boll. Bands : Lower [{latest['BB_Lower']:.2f}] <-> Mid [{latest['BB_Mid']:.2f}] <-> Upper [{latest['BB_Upper']:.2f}]
VWAP        : {latest['VWAP']:.2f}"""

    return summary
