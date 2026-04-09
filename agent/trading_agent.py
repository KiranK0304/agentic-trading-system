"""
Trading agent graph — builds and runs the multi-agent LangGraph pipeline.

Graph topology
──────────────
  START → prepare → market_context → fundamental → technical → orchestrator → END

  • prepare        : summarises raw OHLCV DataFrame into text
  • market_context : fetches global indices / sentiment / news
  • fundamental    : sub-agent — analyses from a valuation / macro lens
  • technical      : sub-agent — analyses from a pure price-action lens
  • orchestrator   : synthesises both sub-agents into final BUY / SELL
"""

import pandas as pd
from langgraph.graph import StateGraph, START, END

from .schemas import GraphState, AgentSchema, SubAgentAnalysis
from .nodes import (
    prepare_data_node,
    market_context_node,
    make_fundamental_node,
    make_technical_node,
    make_orchestrator_node,
)
from .llm_factory import build_llm, build_structured_llm, LLMConfig
from datetime import datetime

def build_trading_graph():
    """
    Orchestrates dependency creation and graph assembly.

    1. Creates a single base LLM (Groq).
    2. Wraps it with structured-output for each schema:
       - SubAgentAnalysis  → fundamental & technical nodes
       - AgentSchema       → orchestrator node
    3. Injects the LLMs into node factories.
    4. Wires and compiles the StateGraph.
    """

    # ── 1. Shared LLM config ──
    llm_config = LLMConfig(
        model_name="llama-3.3-70b-versatile",
        temperature=0.0,
    )

    fundamental_llm = build_structured_llm(schema=SubAgentAnalysis,
                                           config=llm_config,
                                           method="function_calling")
                    
    technical_llm = build_structured_llm(schema=SubAgentAnalysis,
                                        config=llm_config,
                                        method="function_calling")

    orchestrator_llm = build_structured_llm(schema=AgentSchema,
                                           config=llm_config,
                                           method="function_calling")

    # ── 3. Build node callables via factories (dependency injection) ──
    fundamental_node  = make_fundamental_node(fundamental_llm)
    technical_node    = make_technical_node(technical_llm)
    orchestrator_node = make_orchestrator_node(orchestrator_llm)

    # ── 4. Assemble the graph ──
    graph_builder = StateGraph(GraphState)

    graph_builder.add_node("prepare",        prepare_data_node)
    graph_builder.add_node("market_context", market_context_node)
    graph_builder.add_node("fundamental",    fundamental_node)
    graph_builder.add_node("technical",      technical_node)
    graph_builder.add_node("orchestrator",   orchestrator_node)

    graph_builder.add_edge(START,             "prepare")
    graph_builder.add_edge("prepare",        "market_context")

    graph_builder.add_edge("market_context", "fundamental")
    graph_builder.add_edge("market_context",    "technical")

    graph_builder.add_edge("technical",      "orchestrator")
    graph_builder.add_edge("fundamental",   "orchestrator")

    graph_builder.add_edge("orchestrator", END)


    return graph_builder.compile()


# ====================== PUBLIC ENTRY POINT ======================

def run_trading_agent(df: pd.DataFrame, symbol: str) -> AgentSchema:
    """
    Main function to call from outside.

    Takes a pandas DataFrame (from fetch_data) and a symbol string.
    Returns the final structured AgentSchema decision.
    """
    if df.empty:
        raise ValueError("DataFrame is empty")

    agent = build_trading_graph()

    initial_state: GraphState = {
        "df": df,
        "symbol": symbol,
        "data_summary": None,
        "decision": None,
        "raw_response": None,
        "market_context": None,
        "max_iterations": 1,
        # Sub-agent outputs — populated by their respective nodes
        "fundamental_analysis": None,
        "technical_analysis": None,
        "run_timestamp": datetime.now().isoformat()
    }

    result = agent.invoke(initial_state)

    # ── Print sub-agent reports ──
    fund = result.get("fundamental_analysis")
    tech = result.get("technical_analysis")

    if fund:
        print(f"\n{'='*50}")
        print(f"  FUNDAMENTAL ANALYSIS — {symbol}")
        print(f"{'='*50}")
        print(f"  Signal     : {fund.signal}")
        print(f"  Confidence : {fund.confidence}%")
        print(f"  Key Factors: {', '.join(fund.key_factors)}")
        print(f"  Analysis   :\n    {fund.analysis[:300]}...")

    if tech:
        print(f"\n{'='*50}")
        print(f"  TECHNICAL ANALYSIS — {symbol}")
        print(f"{'='*50}")
        print(f"  Signal     : {tech.signal}")
        print(f"  Confidence : {tech.confidence}%")
        print(f"  Key Factors: {', '.join(tech.key_factors)}")
        print(f"  Analysis   :\n    {tech.analysis[:300]}...")

    # ── Print final orchestrator decision ──
    decision: AgentSchema = result["decision"]

    print(f"\n{'='*50}")
    print(f"  ORCHESTRATOR DECISION — {symbol}")
    print(f"{'='*50}")
    print(f"  Decision   : {decision.decision}")
    print(f"  Confidence : {decision.confidence}%")
    print(f"  Entry Price: ₹{decision.entry_price:.2f}")
    print(f"\n  Reasoning:\n    {decision.reasoning}")
    print(f"\n  Risk Notes:\n    {decision.risk_notes}")

    return decision
