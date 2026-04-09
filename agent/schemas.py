from pydantic import BaseModel, Field
from typing import Literal

from typing import TypedDict, Annotated, Any
import pandas as pd

from datetime import datetime


# ─────────────── Sub-Agent Output Schema ───────────────
# Used by specialized sub-agents (fundamental, technical).
# Each sub-agent returns a directional signal with reasoning.

class SubAgentAnalysis(BaseModel):
    """Structured output from a specialized analysis sub-agent."""
    analysis: str = Field(
        ...,
        description="Detailed analysis reasoning — cite specific data points and observations",
    )
    signal: Literal["BULLISH", "BEARISH", "NEUTRAL"] = Field(
        ...,
        description="Directional signal: BULLISH, BEARISH, or NEUTRAL",
    )
    confidence: int = Field(
        ...,
        ge=1,
        le=100,
        description="Confidence in the signal (1-100)",
    )
    key_factors: list[str] = Field(
        ...,
        description="Top 3-5 factors driving the signal, each as a short sentence",
    )


# ─────────────── Orchestrator Output Schema ───────────────
# The orchestrator is the final decision-maker. It synthesises
# sub-agent analyses into a single BUY / SELL call.

class AgentSchema(BaseModel):
    """Structured output from the orchestrator (final trading decision)."""
    decision: Literal["BUY", "SELL"] = Field(
        ...,
        description="Final trading decision: BUY or SELL",
    )
    confidence: int = Field(
        ...,
        ge=1,
        le=100,
        description="Confidence score (1-100) in the decision",
    )
    reasoning: str = Field(
        ...,
        description=(
            "Step-by-step synthesis of fundamental + technical analyses, "
            "areas of agreement/conflict, market context, and why this direction was chosen"
        ),
    )
    entry_price: float = Field(
        ...,
        description="Recommended entry/exit price (use the latest Close unless a better level is identified)",
    )
    risk_notes: str = Field(
        ...,
        description="Stop-loss level, key risk factors, and conditions that would invalidate this trade",
    )


# ─────────────── Graph State ───────────────
# TypedDict that flows through every node in the LangGraph pipeline.
# Each node reads what it needs and writes its output back.

class GraphState(TypedDict):
    df: pd.DataFrame
    symbol: str
    data_summary: str | None
    decision: AgentSchema | None
    raw_response: str | None
    max_iterations: Annotated[int, lambda x, y: x + y]
    market_context: dict[str, Any] | None
    # ── sub-agent outputs (added for multi-agent pipeline) ──
    fundamental_analysis: SubAgentAnalysis | None
    technical_analysis: SubAgentAnalysis | None
    run_timestamp: str | None