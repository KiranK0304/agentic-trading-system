import os
from pathlib import Path  
import pandas as pd
from typing import Callable

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .schemas import GraphState, AgentSchema
from scrapper import run_screener_export

FUND_SCRAPER_PATH = Path("/home/Kiran/work/WebScraper/scaper_2.py")
PROMPTS_DIR = Path(__file__).parent / "prompts"
FUNDAMENTALS_PROMPT_PATH = PROMPTS_DIR / "fundamental_system_prompt.md"


# Orchestrator node: prepares the initial GraphState from raw inputs

def orchestrator_node(df: pd.DataFrame, symbol: str) -> GraphState:
    """Create the initial GraphState from raw DataFrame and symbol.

    This node is intended to be the first step in the graph, responsible for
    normalizing the external inputs into the internal GraphState schema.
    """
    if df.empty:
        raise ValueError("DataFrame is empty")

    state: GraphState = {
        "df": df,
        "symbol": symbol,
        "data_summary": None,
        "decision": None,
        "raw_response": None,
        "max_iterations": 1,
        "fundamentals": None,
    }

    return state



def fundamentals_node(state: GraphState) -> GraphState:
    """
    Fundamental analyst node:
    1) Call Screener scraper for this symbol.
    2) Run an LLM that compares fundamentals with the price data in df/data_summary.
    3) Store results in state['fundamentals'].
    """

    symbol = state["symbol"]

    # 1) Call your existing scraper
    fundamentals_dir = "./fundamentals_exports"
    screener_file = run_screener_export(
        query=symbol,
        output_dir=fundamentals_dir,
        login_flag=False,   # or True if you want forced login
        no_login=False,     # will use SCREENER_USER / SCREENER_PASS from .env if present
    )

    screener_path = os.path.abspath(screener_file) if screener_file else None

    # 2) Build an LLM prompt that can compare fundamentals with df/data_summary
    llm = ChatOpenAI(
        model="llama-3.1-8b-instant",
        openai_api_base=os.environ.get("base_url"),
        openai_api_key=os.environ.get("GROQ_API_KEY"),
        temperature=0.1,
    )

    price_summary = state.get("data_summary") or "<no price summary yet>"

    # Load system prompt from file
    if not FUNDAMENTALS_PROMPT_PATH.exists():
        raise FileNotFoundError(f"Fundamentals prompt not found at: {FUNDAMENTALS_PROMPT_PATH}")

    with open(FUNDAMENTALS_PROMPT_PATH, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        (
            "user",
            "Symbol: {symbol}\n"
            "Screener export file: {screener_path}\n\n"
            "Recent price data summary:\n{price_summary}\n\n"
            "1) Give a concise but detailed fundamental view of the company.\n"
            "2) Comment on whether the recent price action seems overvalued, "
            "undervalued, or roughly aligned with fundamentals, and why."
        ),
    ])

    chain = prompt | llm
    response = chain.invoke(
        {
            "symbol": symbol,
            "screener_path": screener_path or "<no fundamentals file>",
            "price_summary": price_summary,
        }
    )

    analysis_text = getattr(response, "content", str(response))

    state["fundamentals"] = {
        "source": screener_path,
        "qualitative_view": analysis_text,
        "alignment_with_price_action": "See qualitative_view for details.",
    }

    return state




def prepare_data_node(state: GraphState) -> GraphState:
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
    print("prepp worked")
    return state




def make_analyze_node(llm_with_structured_output, summary_dir: Path | None = None,) -> Callable[[GraphState], GraphState]:
    """
    Factory function that injects dependencies and returns a LangGraph-compatible node.
    Called once during graph construction.
    """
    
    # Resolve paths once at factory time (not on every invocation)
    if summary_dir is None:
        # Make this configurable in the future (env var, config object, etc.)
        summary_dir = Path("/home/Kiran/work/Langgraph_Project/Summary")
    
    prompt_path = Path(__file__).parent / "prompts" / "trading_system_prompt.md"
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"System prompt not found at: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    # Build prompt template once (performance + cleanliness)
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Here is the 5-minute OHLCV data for analysis:\n\n{data_summary}\n\nProvide your trading decision now.")
    ])

    def analyze_node(state: GraphState) -> GraphState:
        """The actual node function used by LangGraph.
        It only depends on state + the dependencies captured via closure."""
        
        # File I/O (still present — we can extract later if needed)
        summary_path = summary_dir / f"summary_{state.get('symbol', 'unknown')}.txt"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(state.get("data_summary", ""))

        # Use the injected structured LLM
        chain = prompt_template | llm_with_structured_output

        response: AgentSchema = chain.invoke({
            "data_summary": state.get("data_summary", "")
        })

        # Update state (your current mutable style — works fine)
        state["decision"] = response
        state["raw_response"] = str(response)
        print("dep worked")
        
        return state

    return analyze_node
