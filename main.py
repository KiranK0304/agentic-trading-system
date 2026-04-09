# Agentic Trading System — CLI entry point
from agent.trading_agent import run_trading_agent
from utils.data_loader import fetch_data


print("Enter the stock symbol")
print("    eg: SBIN.NS, TCS.NS, LT.NS")

symbol = input("Enter:  ")

# period="5d" + interval="5m" is the safe combo for Yahoo Finance.
# period="max" with 5m interval returns empty/broken data.
df = fetch_data(symbol)

if not df.empty:
    decision = run_trading_agent(df, symbol=symbol)

    # Quick summary after the full agent report
    if decision.decision == "BUY" and decision.confidence > 70:
        print("\n🟢 Strong BUY signal from agent!")
    elif decision.decision == "SELL" and decision.confidence > 70:
        print("\n🔴 Strong SELL signal from agent!")
    else:
        print(f"\n⚪ {decision.decision} with moderate confidence ({decision.confidence}%)")
else:
    print(f"\n❌ Could not fetch data for {symbol}. Check the symbol and try again.")