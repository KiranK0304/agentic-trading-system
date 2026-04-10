import pandas as pd
from langgraph.graph import StateGraph, START, END
from langgraph.graph import END, StateGraph

from .schemas import GraphState, AgentSchema, SubAgentAnalysis, RiskReview
from .nodes import (
    prepare_data_node,
    market_context_node,
    make_fundamental_node,
    make_technical_node,
    make_orchestrator_node,
    make_risk_manager_node,        # ← Added
)
from .llm_factory import build_structured_llm, LLMConfig
from datetime import datetime


def route_after_orchestrator(state: GraphState) -> str:
    """Conditional routing after orchestrator.
    
    - First pass (no risk_review yet) → go to risk_manager
    - Second pass (risk_review exists) → go to END
    """
    if state.get("risk_review") is None:
        return "risk_manager"
    return END


def build_trading_graph():
    """
    Builds the complete trading analysis graph with:
    - Parallel sub-agents (Fundamental + Technical)
    - Orchestrator (first pass)
    - Risk Manager
    - Orchestrator (second pass - re-evaluation)
    """

    # ── LLM Configurations ─────────────────────────────────────
    subagent_conf = LLMConfig(
        model_name="llama-3.1-8b-instant",
        temperature=0.2,
    )

    orchestrator_conf = LLMConfig(
        model_name="llama-3.3-70b-versatile",
        temperature=0.0,
    )

    risk_conf = LLMConfig(
        model_name="llama-3.3-70b-versatile",
        temperature=0.1,          # Slightly more conservative for risk
    )

    # ── Build Structured LLMs ──────────────────────────────────
    fundamental_llm = build_structured_llm(
        schema=SubAgentAnalysis,
        config=subagent_conf,
        method="function_calling"
    )

    technical_llm = build_structured_llm(
        schema=SubAgentAnalysis,
        config=subagent_conf,
        method="function_calling"
    )

    orchestrator_llm = build_structured_llm(
        schema=AgentSchema,
        config=orchestrator_conf,
        method="function_calling"
    )

    risk_manager_llm = build_structured_llm(
        schema=RiskReview,
        config=risk_conf,
        method="function_calling"
    )

    # ── Create node instances via factories ────────────────────
    fundamental_node = make_fundamental_node(fundamental_llm)
    technical_node = make_technical_node(technical_llm)
    orchestrator_node = make_orchestrator_node(orchestrator_llm)
    risk_manager_node = make_risk_manager_node(risk_manager_llm)

    # ── Assemble the StateGraph ────────────────────────────────
    graph_builder = StateGraph(GraphState)

    # Add nodes
    graph_builder.add_node("prepare",         prepare_data_node)
    graph_builder.add_node("market_context",  market_context_node)
    graph_builder.add_node("fundamental",     fundamental_node)
    graph_builder.add_node("technical",       technical_node)
    graph_builder.add_node("orchestrator",    orchestrator_node)
    graph_builder.add_node("risk_manager",    risk_manager_node)

    # ── Define edges ───────────────────────────────────────────
    graph_builder.add_edge(START, "prepare")
    graph_builder.add_edge("prepare", "market_context")

    # Parallel execution of sub-agents
    graph_builder.add_edge("market_context", "fundamental")
    graph_builder.add_edge("market_context", "technical")

    # Both sub-agents converge to first orchestrator pass
    graph_builder.add_edge("fundamental", "orchestrator")
    graph_builder.add_edge("technical", "orchestrator")

    # Conditional routing after orchestrator (your function)
    graph_builder.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "risk_manager": "risk_manager",
            END: END
        }
    )

    # After risk review, always go back to orchestrator for final re-evaluation
    graph_builder.add_edge("risk_manager", "orchestrator")

    # The second orchestrator pass will route to END via the conditional edge

    return graph_builder.compile()


# ====================== PUBLIC ENTRY POINT ======================

def run_trading_agent(df: pd.DataFrame, symbol: str) -> AgentSchema:
    """
    Main entry point: Runs the full pipeline including risk management 
    and final re-evaluated decision.
    """
    if df.empty:
        raise ValueError("DataFrame is empty")

    agent = build_trading_graph()

    initial_state: GraphState = {
        "df": df,
        "symbol": symbol,
        "run_timestamp": datetime.now().isoformat(),
        
        # Will be populated by nodes
        "data_summary": None,
        "market_context": None,
        "fundamental_analysis": None,
        "technical_analysis": None,
        "decision": None,
        "raw_response": None,
        "risk_review": None,           # Critical for routing
    }

    # Execute the full graph
    result = agent.invoke(initial_state)

    # ── Pretty Printing ────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  TRADING ANALYSIS REPORT — {symbol.upper()}")
    print(f"{'='*70}")

    # Sub-agents
    fund = result.get("fundamental_analysis")
    tech = result.get("technical_analysis")

    if fund:
        print(f"\nFUNDAMENTAL ANALYSIS")
        print(f"  Signal      : {fund.signal}")
        print(f"  Confidence  : {fund.confidence}%")
        print(f"  Key Factors : {', '.join(fund.key_factors)}")
        print(f"  Analysis    : {fund.analysis[:450]}{'...' if len(fund.analysis) > 450 else ''}")

    if tech:
        print(f"\nTECHNICAL ANALYSIS")
        print(f"  Signal      : {tech.signal}")
        print(f"  Confidence  : {tech.confidence}%")
        print(f"  Key Factors : {', '.join(tech.key_factors)}")
        print(f"  Analysis    : {tech.analysis[:450]}{'...' if len(tech.analysis) > 450 else ''}")

    # Risk Manager Review
    risk = result.get("risk_review")
    if risk:
        print(f"\n{'─'*60}")
        print(f"RISK MANAGER REVIEW")
        print(f"  Verdict         : {risk.verdict}")
        print(f"  Risk Level      : {risk.risk_level}")
        if risk.confidence_adjustment is not None:
            print(f"  Confidence Adj. : {risk.confidence_adjustment}%")
        print(f"  Critique        :\n    {risk.critique}")

    # Final Decision (after risk re-evaluation)
    decision: AgentSchema = result["decision"]

    print(f"\n{'='*70}")
    print(f"  FINAL DECISION (After Risk Review) — {symbol.upper()}")
    print(f"{'='*70}")
    print(f"  Decision     : {decision.decision}")
    print(f"  Confidence   : {decision.confidence}%")
    print(f"  Entry Price  : ₹{decision.entry_price:.2f}")
    print(f"\n  Reasoning:\n    {decision.reasoning}")
    print(f"\n  Risk Notes:\n    {decision.risk_notes}")
    print(f"\n  FT Summary:\n    {decision.ft_summary}")

    return decision