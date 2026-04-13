import concurrent.futures
from agent.trading_agent import run_trading_agent
from utils.data_loader import get_live_info, get_historical_data

TARGET_ASSET = "NIFTY 50"

def main():
    print(f"Starting execution for {TARGET_ASSET}...")
    
    # Run API fetches concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_live = executor.submit(get_live_info, TARGET_ASSET)
        future_hist = executor.submit(get_historical_data, TARGET_ASSET, "5d", "5m")
        
        live_snapshot = future_live.result()
        df = future_hist.result()

    if df.empty:
        print(f"\n❌ Could not fetch historical data for {TARGET_ASSET}. Exiting.")
        return

    # Pass both live snapshot and historical data to the trading agent
    decision = run_trading_agent(df=df, symbol=TARGET_ASSET, live_snapshot=live_snapshot)

    # Quick summary after the full agent report
    if decision.decision == "BUY" and decision.confidence > 70:
        print("\n🟢 Strong BUY signal from agent for futures!")
    elif decision.decision == "SELL" and decision.confidence > 70:
        print("\n🔴 Strong SELL signal from agent for futures!")
    else:
        print(f"\n⚪ {decision.decision} with moderate confidence ({decision.confidence}%)")

if __name__ == "__main__":
    main()