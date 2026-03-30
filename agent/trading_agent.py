import pandas as pd
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from .schemas import TradingDecision

if os.environ["GROQ_API_KEY"]:  
    print("yes!")
else: 
    raise ValueError("key is not set")

llm = ChatOpenAI(
    model="llama-3.1-8b-instant",
    openai_api_base=os.environ.get("base_url"),
    openai_api_key=os.environ.get("GROQ_API_KEY"),
    temperature=0.1
)

llm_with_structured_output = llm.with_structured_output(TradingDecision, method="function_calling")

# ====================== STATE ======================
class AgentState(TypedDict):
    df: pd.DataFrame                    # Input price data
    symbol: str
    data_summary: str  | None
    decision: TradingDecision | None    # Final structured output
    raw_response: str | None            # For debugging
    max_iterations: Annotated[int, lambda x, y: x + y]   # Optional iteration counter


# ====================== NODES ======================
def prepare_data_node(state: AgentState) -> AgentState:
    """Prepare a clean summary + recent data for the LLM."""
    df = state["df"]
    
    if len(df) < 10:
        raise ValueError(f"Not enough data. Got only {len(df)} rows.")

    # Safe scalar extraction (recommended way)
    latest_close = df['Close'].iloc[-1].item()
    latest_high  = df['High'].iloc[-1].item()
    latest_low   = df['Low'].iloc[-1].item()
    avg_volume   = int(df['Volume'].mean().item())

    start_time = df['Datetime_IST'].iloc[0]
    end_time   = df['Datetime_IST'].iloc[-1]

    summary = f"""
Symbol: {state['symbol']}
Total 5-min bars: {len(df)}
Time range: {start_time} → {end_time}
Latest Close: ₹{latest_close:.2f}
Latest High : ₹{latest_high:.2f}
Latest Low  : ₹{latest_low:.2f}
Average Volume: {avg_volume:,}
    """.strip()

    recent_data = df.tail(25)[['Open', 'High', 'Low', 'Close', 'Volume']].round(2).to_string()

    state["data_summary"] = f"{summary}\n\nLast 25 candles:\n{recent_data}"
    return state



def analyze_node(state: AgentState) -> AgentState:
    """Call the trading agent with system prompt using correct path."""
    prompt_path = Path(__file__).parent / "prompts" / "trading_system_prompt.md"
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"System prompt not found at: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Here is the 5-minute OHLCV data for analysis:\n\n{data_summary}\n\nProvide your trading decision now.")
    ])

    # /home/Kiran/work/Langgraph_Project/Summary

    with open(f'/home/Kiran/work/Langgraph_Project/Summary/summary_{state["symbol"]}.txt', 'w') as f:
        f.write(state["data_summary"])

    chain = prompt_template | llm_with_structured_output

    response: TradingDecision = chain.invoke({"data_summary": state["data_summary"]})

    state["decision"] = response
    state["raw_response"] = str(response)
    return state


# ====================== GRAPH ======================
def create_trading_agent():
    graph = StateGraph(AgentState)
    
    graph.add_node("prepare_data", prepare_data_node)
    graph.add_node("analyze", analyze_node)
    
    graph.add_edge(START, "prepare_data")
    graph.add_edge("prepare_data", "analyze")
    graph.add_edge("analyze", END)
    
    return graph.compile()


# ====================== PUBLIC FUNCTION ======================
def run_trading_agent(df: pd.DataFrame, symbol: str) -> TradingDecision:
    """
    Main function to call from outside.
    Takes pandas DataFrame (from your fetch_5min_data) and returns structured decision.
    """
    if df.empty:
        raise ValueError("DataFrame is empty")

    agent = create_trading_agent()
    
    initial_state: AgentState = {
        "df": df,
        "symbol": symbol,
        "decision": None,
        "raw_response": None,
        "max_iterations": 1,   # not really used yet
        "data_summary": ""     # will be filled by node
    }
    
    result = agent.invoke(initial_state)
    
    decision: TradingDecision = result["decision"]
    
    print(f"\n=== AGENT DECISION for {symbol} ===")
    print(f"Decision   : {decision.decision}")
    print(f"Confidence : {decision.confidence}%")
    print(f"Entry Price: ₹{decision.entry_price:.2f}")
    print(f"\nReasoning:\n{decision.reasoning}")
    print(f"\nRisk Notes:\n{decision.risk_notes}")
    
    return decision