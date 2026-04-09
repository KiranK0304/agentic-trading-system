"""
Graph node functions for the multi-agent trading pipeline.

Architecture
────────────
prepare_data_node      → Builds text summary from raw OHLCV DataFrame
market_context_node    → Fetches global indices / sentiment / headlines
make_fundamental_node  → Factory: returns a fundamental-analysis sub-agent node
make_technical_node    → Factory: returns a technical-analysis sub-agent node
make_orchestrator_node → Factory: returns the orchestrator (final decision-maker)

Every "make_*" factory follows dependency-injection via closure:
  1. Called ONCE at graph-build time with the injected LLM + config.
  2. Returns a plain `(state) -> state` callable used by LangGraph at runtime.
"""

from pathlib import Path
import pandas as pd
from typing import Callable

from langchain_core.prompts import ChatPromptTemplate

from .schemas import GraphState, AgentSchema, SubAgentAnalysis
from utils.market_context import build_market_context_payload

# Project root — used for portable file paths (no more hardcoded absolutes)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ──────────────────────────────────────────────────────────
#  Shared helpers
# ──────────────────────────────────────────────────────────

def _load_prompt(filename: str) -> str:
    """Load a prompt markdown file from agent/prompts/."""
    prompt_path = Path(__file__).parent / "prompts" / filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def _get_macro_context(state: GraphState) -> str:
    """Extract the LLM-readable macro context string from state."""
    fallback = "No global market context available."
    if state.get("market_context"):
        derived = state["market_context"].get("derived", {})
        return derived.get("llm_context", fallback)
    return fallback


# ──────────────────────────────────────────────────────────
#  Node 1: prepare_data_node
# ──────────────────────────────────────────────────────────

def prepare_data_node(state: GraphState) -> GraphState:
    """Prepare a clean text summary + recent candle table for the LLM."""
    df = state["df"]

    if len(df) < 10:
        raise ValueError(f"Not enough data. Got only {len(df)} rows.")

    # Safe scalar extraction
    latest_close = df['Close'].iloc[-1].item()
    latest_high  = df['High'].iloc[-1].item()
    latest_low   = df['Low'].iloc[-1].item()
    avg_volume   = int(df['Volume'].mean().item())

    start_time = df['Datetime_IST'].iloc[0]
    end_time   = df['Datetime_IST'].iloc[-1]

    summary = f"""\
Symbol: {state['symbol']}
Total 5-min bars: {len(df)}
Time range: {start_time} → {end_time}
Latest Close: ₹{latest_close:.2f}
Latest High : ₹{latest_high:.2f}
Latest Low  : ₹{latest_low:.2f}
Average Volume: {avg_volume:,}"""

    recent_data = (
        df.tail(25)[['Open', 'High', 'Low', 'Close', 'Volume']]
        .round(2)
        .to_string()
    )

    state["data_summary"] = f"{summary}\n\nLast 25 candles:\n{recent_data}"

    return state


# ──────────────────────────────────────────────────────────
#  Node 2: market_context_node
# ──────────────────────────────────────────────────────────

def market_context_node(state: GraphState) -> GraphState:
    """Fetch global index levels, Fear & Greed, and general market headlines."""
    state["market_context"] = build_market_context_payload(
        symbol_for_filename=state["symbol"],
    )
    return state


# ──────────────────────────────────────────────────────────
#  Node 3: Fundamental analysis sub-agent  (factory)
# ──────────────────────────────────────────────────────────

def make_fundamental_node(
    llm_with_structured_output,
) -> Callable[[GraphState], GraphState]:
    """
    Factory: builds the fundamental-analysis node.

    The LLM is injected at graph-build time; the returned callable
    is the actual node function used by LangGraph at runtime.
    """
    system_prompt = _load_prompt("fundamental_system_prompt.md")

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user",
         "Here is the data for fundamental analysis:\n\n"
         "{data_context}\n\n"
         "Global market context:\n{macro_context}\n\n"
         "Provide your fundamental analysis now."),
    ])

    def fundamental_node(state: GraphState) -> GraphState:

        """Run the fundamental analysis sub-agent."""
        data_context  = state.get("data_summary", "No data available.")
        macro_context = _get_macro_context(state)

        chain = prompt_template | llm_with_structured_output
        result: SubAgentAnalysis = chain.invoke({
            "data_context":  data_context,
            "macro_context": macro_context,
        })

        state["fundamental_analysis"] = result

        print(""" 
        this node used data summary and called get macro function
        that function returns something like derived some embedded type thing
        then use summary and macro context to invoke the chain and 
        that will produce something
        found build_structured_llm but didnt see anywhere used
        finally this node will fill fundamental_analysis field""")

        return state

    return fundamental_node


# ──────────────────────────────────────────────────────────
#  Node 4: Technical analysis sub-agent  (factory)
# ──────────────────────────────────────────────────────────

def make_technical_node(
    llm_with_structured_output,
) -> Callable[[GraphState], GraphState]:
    """
    Factory: builds the technical-analysis node.

    Same injection pattern as the fundamental node.
    """
    system_prompt = _load_prompt("technical_system_prompt.md")

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user",
         "Here is the 5-minute OHLCV data for technical analysis:\n\n"
         "{data_context}\n\n"
         "Global market context:\n{macro_context}\n\n"
         "Provide your technical analysis now."),
    ])

    def technical_node(state: GraphState) -> GraphState:


        """Run the technical analysis sub-agent."""
        data_context  = state.get("data_summary", "No data available.")
        macro_context = _get_macro_context(state)

        chain = prompt_template | llm_with_structured_output
        result: SubAgentAnalysis = chain.invoke({
            "data_context":  data_context,
            "macro_context": macro_context,
        })

        state["technical_analysis"] = result

        return state

    return technical_node


# ──────────────────────────────────────────────────────────
#  Node 5: Orchestrator — final decision-maker  (factory)
# ──────────────────────────────────────────────────────────

def make_orchestrator_node(
    llm_with_structured_output,
    summary_dir: Path | None = None,
) -> Callable[[GraphState], GraphState]:
    """
    Factory: builds the orchestrator node.

    The orchestrator reads outputs from BOTH sub-agents (fundamental
    and technical), plus the raw data summary and macro context,
    and produces the final BUY / SELL decision via AgentSchema.
    """
    if summary_dir is None:
        summary_dir = PROJECT_ROOT / "Summary"

    system_prompt = _load_prompt("orchestrator_system_prompt.md")

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user",
         "Here is the complete analysis context for your final decision:\n\n"
         "## Raw Market Data\n{data_summary}\n\n"
         "## Global Market Context\n{macro_context}\n\n"
         "## Fundamental Analysis (Sub-Agent)\n{fundamental_analysis}\n\n"
         "## Technical Analysis (Sub-Agent)\n{technical_analysis}\n\n"
         "Synthesize all inputs and provide your final trading decision now."),
    ])

    def orchestrator_node(state: GraphState) -> GraphState:
        """
        Orchestrator: synthesises fundamental + technical + macro
        into a final BUY / SELL decision.
        """
        print("time:",state["run_timestamp"])
        # ── persist data summary to disk ──
        summary_path = summary_dir / f"summary_{state.get('symbol', 'unknown')}.txt"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(state.get("data_summary", ""))

        # ── build context strings ──
        data_summary  = state.get("data_summary", "No data available.")
        macro_context = _get_macro_context(state)

        # ── format sub-agent outputs for the LLM ──
        fund = state.get("fundamental_analysis")
        tech = state.get("technical_analysis")

        fund_text = "No fundamental analysis available."
        if fund:
            fund_text = (
                f"Signal: {fund.signal} (Confidence: {fund.confidence}%)\n"
                f"Analysis: {fund.analysis}\n"
                f"Key Factors: {', '.join(fund.key_factors)}"
            )

        tech_text = "No technical analysis available."
        if tech:
            tech_text = (
                f"Signal: {tech.signal} (Confidence: {tech.confidence}%)\n"
                f"Analysis: {tech.analysis}\n"
                f"Key Factors: {', '.join(tech.key_factors)}"
            )

        # ── invoke the orchestrator LLM ──
        chain = prompt_template | llm_with_structured_output
        response: AgentSchema = chain.invoke({
            "data_summary":            data_summary,
            "macro_context":           macro_context,
            "fundamental_analysis":    fund_text,
            "technical_analysis":      tech_text,
        })

        state["decision"]     = response
        state["raw_response"] = str(response)
        return state

    return orchestrator_node
