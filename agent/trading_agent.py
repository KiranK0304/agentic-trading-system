import pandas as pd
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pathlib import Path
from .schemas import GraphState, AgentSchema
from .nodes import make_analyze_node
from .llm_factory import build_llm, LLMConfig



def build_trading_graph():
    """Orchestrates dependency creation and graph assembly."""
    
    # 1. Create LLM and structured version once (centralized)
    llm_config = LLMConfig(
        model_name="llama-3.3-70b-versatile",   # Change easily here or load from env/config
        temperature=0.0
    )
    base_llm = build_llm(llm_config)
    structured_llm = base_llm.with_structured_output(AgentSchema, method="function_calling")   # Adjust schema name if needed

    # 2. Inject dependencies into the node factory
    analyze_node = make_analyze_node(
        llm_with_structured_output=structured_llm, 
        # Optional overrides for testing or different environments:
        # summary_dir=Path("/tmp/test_summaries")
    )

    # 3. Build the graph (clean wiring)
    from langgraph.graph import StateGraph, END   # or START, etc.

    graph_builder = StateGraph(GraphState)
    
    graph_builder.add_node("analyze", analyze_node)
    
    graph_builder.set_entry_point("analyze")    
    return graph_builder.compile()

# ====================== GRAPH ======================
# def create_trading_agent():
#     graph = StateGraph(GraphState)
    
#     graph.add_node("prepare_data", prepare_data_node)
#     graph.add_node("analyze", analyze_node)
    
#     graph.add_edge(START, "prepare_data")
#     graph.add_edge("prepare_data", "analyze")
#     graph.add_edge("analyze", END)
    
#     return graph.compile()


# ====================== PUBLIC FUNCTION ======================
def run_trading_agent(df: pd.DataFrame, symbol: str) -> AgentSchema:
    """
    Main function to call from outside.
    Takes pandas DataFrame (from your fetch_5min_data) and returns structured decision.
    """
    if df.empty:
        raise ValueError("DataFrame is empty")

    agent = build_trading_graph()
    
    initial_state: GraphState = {
        "df": df,
        "symbol": symbol,
        "decision": None,
        "raw_response": None,
        "max_iterations": 1,   # not really used yet
        "data_summary": ""     # will be filled by node
    }
    
    result = agent.invoke(initial_state)
    
    decision: AgentSchema = result["decision"]
    
    print(f"\n=== AGENT DECISION for {symbol} ===")
    print(f"Decision   : {decision.decision}")
    print(f"Confidence : {decision.confidence}%")
    print(f"Entry Price: ₹{decision.entry_price:.2f}")
    print(f"\nReasoning:\n{decision.reasoning}")
    print(f"\nRisk Notes:\n{decision.risk_notes}")
    
    return decision

