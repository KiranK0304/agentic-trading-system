"""
SSE streaming wrapper around the LangGraph trading pipeline.

Yields JSON events as each node completes, so the frontend
can render agent cards one-by-one in real time.
"""

import json
import asyncio
from datetime import datetime
from typing import AsyncGenerator

import pandas as pd

from agent.trading_agent import build_trading_graph
from agent.schemas import GraphState
from utils.data_loader import get_live_info, get_historical_data


TARGET_ASSET = "NIFTY 50"

# Human-readable labels for each node
NODE_LABELS = {
    "prepare": "Data Preparation",
    "market_context": "Market Context",
    "fundamental": "Fundamental Analysis",
    "technical": "Technical Analysis",
    "orchestrator": "Orchestrator",
    "risk_manager": "Risk Manager",
}


def _sse(payload: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(payload)}\n\n"


def _serialize_node_output(node_name: str, data: dict, state: dict) -> dict:
    """Convert raw node output into a clean JSON-serializable event."""

    if node_name == "fundamental":
        analysis = state.get("fundamental_analysis")
        if analysis:
            return {
                "step": "fundamental",
                "label": "Fundamental Analysis",
                "signal": analysis.signal,
                "confidence": analysis.confidence,
                "key_factors": analysis.key_factors,
                "analysis": analysis.analysis,
            }

    elif node_name == "technical":
        analysis = state.get("technical_analysis")
        if analysis:
            return {
                "step": "technical",
                "label": "Technical Analysis",
                "signal": analysis.signal,
                "confidence": analysis.confidence,
                "key_factors": analysis.key_factors,
                "analysis": analysis.analysis,
            }

    elif node_name == "risk_manager":
        risk = state.get("risk_review")
        if risk:
            return {
                "step": "risk_manager",
                "label": "Risk Manager Review",
                "verdict": risk.verdict,
                "risk_level": risk.risk_level,
                "confidence_adjustment": risk.confidence_adjustment,
                "critique": risk.critique,
            }

    elif node_name == "orchestrator":
        decision = state.get("decision")
        risk_review = state.get("risk_review")
        if decision:
            is_final = risk_review is not None
            return {
                "step": "orchestrator_final" if is_final else "orchestrator_initial",
                "label": "Final Decision (After Risk Review)" if is_final else "Initial Orchestrator Decision",
                "decision": decision.decision,
                "confidence": decision.confidence,
                "entry_price": decision.entry_price,
                "reasoning": decision.reasoning,
                "risk_notes": decision.risk_notes,
                "ft_summary": decision.ft_summary,
            }

    elif node_name == "prepare":
        row_count = len(state.get("df", []))
        return {
            "step": "prepare",
            "label": "Data Preparation",
            "message": f"Prepared {row_count} candles with technical indicators.",
        }

    elif node_name == "market_context":
        ctx = state.get("market_context", {})
        derived = ctx.get("derived", {})
        return {
            "step": "market_context",
            "label": "Market Context",
            "fear_greed": derived.get("fear_greed_label", "N/A"),
            "fear_greed_value": derived.get("fear_greed_value", "N/A"),
            "breadth": derived.get("breadth", "N/A"),
            "headline_count": derived.get("headline_count", 0),
        }

    return {"step": node_name, "label": NODE_LABELS.get(node_name, node_name), "message": "Completed."}


async def stream_trading_analysis() -> AsyncGenerator[str, None]:
    """
    Run the full trading pipeline and yield SSE events
    as each graph node completes.
    """

    # 1. Emit a "fetching data" event
    yield _sse({"step": "init", "label": "Initializing", "message": f"Fetching data for {TARGET_ASSET}..."})

    # 2. Fetch data (run in thread to not block the event loop)
    loop = asyncio.get_event_loop()
    live_snapshot, df = await asyncio.gather(
        loop.run_in_executor(None, get_live_info, TARGET_ASSET),
        loop.run_in_executor(None, get_historical_data, TARGET_ASSET, "5d", "5m"),
    )

    if df.empty:
        yield _sse({"step": "error", "label": "Error", "message": "Failed to fetch historical data."})
        return

    source_name = live_snapshot.get("source", "N/A")
    yield _sse({
        "step": "data_ready",
        "label": "Data Ready",
        "message": f"Fetched {len(df)} candles. Live snapshot source: {source_name}.",
    })

    # 3. Build graph and initial state
    agent = build_trading_graph()

    running_state: GraphState = {
        "df": df,
        "symbol": TARGET_ASSET,
        "live_snapshot": live_snapshot,
        "run_timestamp": datetime.now().isoformat(),
        "data_summary": None,
        "fundamental_context": None,
        "market_context": None,
        "fundamental_analysis": None,
        "technical_analysis": None,
        "decision": None,
        "raw_response": None,
        "risk_review": None,
    }

    # 4. Stream through the graph node-by-node
    try:
        for event in agent.stream(running_state):
            for node_name, node_output in event.items():
                # Merge node output into running state for context
                if isinstance(node_output, dict):
                    running_state.update(node_output)

                payload = _serialize_node_output(node_name, node_output, running_state)
                yield _sse(payload)
    except Exception as e:
        yield _sse({"step": "error", "label": "Pipeline Error", "message": str(e)})

    # 5. Done
    yield _sse({"step": "done", "label": "Complete", "message": "Analysis complete."})
