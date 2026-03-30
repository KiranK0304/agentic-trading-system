# After fetching data with your existing function
from agent.trading_agent import run_trading_agent
from data_loader import fetch_data

symbol = "SBIN.NS"

df = fetch_data(symbol, period="max")

if not df.empty:
    decision = run_trading_agent(df, symbol=symbol)
    
    # Example: Use the decision
    if decision.decision == "BUY" and decision.confidence > 70:
        print("Strong BUY signal from agent!")
    elif decision.decision == "SELL":
        print("Agent suggests exiting or shorting.")