import pandas as pd
import matplotlib.pyplot as plt
from sys_1 import fetch_data

def dummy_agent(df_seen):
    """
    A placeholder for your actual LangGraph/LLM agent.
    This agent gets the seen data and should return 'buy' or 'sell'.
    For now, it uses a simple Moving Average crossover logic.
    """
    if len(df_seen) < 20:
        return "hold"
    
    # Calculate a simple 20-period moving average
    sma_20 = df_seen['Close'].rolling(window=20).mean().iloc[-1]
    
    # Use pandas item() or generic float casting to avoid warnings
    current_price = float(df_seen['Close'].iloc[-1])
    
    # Here is where you would normally call your LLM or LangGraph agent, e.g.:
    # prompt = f"Here is the recent price data: {df_seen.tail(20).to_string()}. Should I buy or sell?"
    # return llm.invoke(prompt)
    
    if current_price > sma_20:
        return "buy"
    elif current_price < sma_20:
        return "sell"
    else:
        return "hold"

def evaluate_agent(df, future_window=10):
    """
    Evaluates an agent by splitting the DataFrame so the agent only sees
    all data EXCEPT the last `future_window` rows. The agent predicts,
    and we use the last `future_window` rows to test its prediction.
    """
    if len(df) <= future_window:
        print(f"Not enough data to split. Need more than {future_window} rows, got {len(df)}.")
        return
    
    # Split the data into "seen" (past) and "future" (unseen)
    split_idx = len(df) - future_window
    df_seen = df.iloc[:split_idx].copy()
    df_future = df.iloc[split_idx:].copy()
    
    print(f"\n--- Data Split Info ---")
    print(f"Total rows: {len(df)}")
    print(f"Rows visible to Agent: {len(df_seen)} (up to {df_seen.index.max()})")
    print(f"Future rows for Evaluation: {len(df_future)} (from {df_future.index.min()})\n")
    
    # 1. Optionally plot the data the agent sees BEFORE it decides
    # plt.figure(figsize=(10, 5))
    # plt.plot(df_seen['Datetime_IST'], df_seen['Close'], label="Data Seen by Agent", color="blue")
    # plt.title("Stock Price Data Given to Agent")
    # plt.legend()
    # plt.show()
    
    # 2. Get the agent's prediction based ONLY on df_seen
    print("Calling agent...")
    prediction = dummy_agent(df_seen).lower()
    print(f"🤖 Agent decided to: {prediction.upper()}")
    
    # 3. Evaluate the prediction against the future
    last_seen_price = float(df_seen['Close'].iloc[-1])
    final_future_price = float(df_future['Close'].iloc[-1])
    price_change = final_future_price - last_seen_price
    
    print(f"\n--- Evaluation ---")
    print(f"Price at time of prediction: {last_seen_price:.2f}")
    print(f"Price after {future_window} intervals: {final_future_price:.2f}")
    print(f"Net price change: {price_change:.2f}")
    
    is_success = False
    if prediction == "buy":
        is_success = price_change > 0
    elif prediction == "sell":
        is_success = price_change < 0
        
    if prediction in ["buy", "sell"]:
        if is_success:
            print("✅ SUCCESS: The agent made the correct call!")
        else:
            print("❌ FAILED: The agent made the wrong call!")
    else:
        print("Agent decided to HOLD. No clear success/fail.")
        
    # 4. Plot the final results line graph to visualize the split and the outcome
    plt.figure(figsize=(12, 6))
    
    # Plot historical seen data
    plt.plot(df_seen['Datetime_IST'], df_seen['Close'], label="Seen Data", color="blue")
    
    # Plot future unseen data
    plt.plot(df_future['Datetime_IST'], df_future['Close'], label="Future Data (Outcome)", color="orange", linewidth=2)
    
    # Mark the decision point
    plt.scatter([df_seen['Datetime_IST'].iloc[-1]], [last_seen_price], color='red', s=100, zorder=5, 
                label=f"Decision Point: {prediction.upper()}")
                
    title_text = f"{df['Symbol'].iloc[0]} - Agent Evaluation ({prediction.upper()})"
    if prediction in ["buy", "sell"]:
        title_text += " | Result: " + ("WON ✅" if is_success else "LOST ❌")
        
    plt.title(title_text)
    plt.xlabel("Time")
    plt.ylabel("Close Price")
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    
    # Save the plot instead of showing it, so it doesn't block terminal execution
    plot_filename = f"{df['Symbol'].iloc[0]}_evaluation.png"
    plt.savefig(plot_filename)
    print(f"\nSaved evaluation line graph to {plot_filename}")
    
    # If the environment supports UI, you can also do plt.show()
    # plt.show()

if __name__ == "__main__":
    # Fetch Data using your existing function
    symbol = "HDFCBANK.NS"
    print(f"Fetching data for {symbol}...")
    df_stock = fetch_data(symbol, period="5d", interval="5m")
    
    if not df_stock.empty:
        # We hold out the last 10 rows for evaluation
        evaluate_agent(df_stock, future_window=10)
