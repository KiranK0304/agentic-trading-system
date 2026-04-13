from pydantic import BaseModel, Field
from typing import Literal, Optional, TypedDict, Any
import pandas as pd


class SubAgentAnalysis(BaseModel):
    """Structured output from fundamental or technical analysis sub-agents."""
    analysis: str = Field(
        ...,
        description="Detailed analysis reasoning — cite specific data points, patterns, and observations from the provided data and market context.",
    )
    signal: Literal["BULLISH", "BEARISH", "NEUTRAL"] = Field(
        ...,
        description="Clear directional signal based on the analysis.",
    )
    confidence: int = Field(
        ..., 
        ge=1, 
        le=100,
        description="Confidence in the signal (1-100). Be honest about uncertainty.",
    )
    key_factors: list[str] = Field(
        ...,
        description="Top 3-5 most important factors driving the signal. Each as a short, concise sentence.",
    )


class AgentSchema(BaseModel):
    """Structured output from the orchestrator (final trading decision)."""
    decision: Literal["BUY", "SELL"] = Field(
        ...,
        description="Final trading decision: BUY or SELL. Do not output HOLD.",
    )
    confidence: int = Field(
        ..., 
        ge=1, 
        le=100,
        description="Overall confidence in this trading decision (1-100).",
    )
    reasoning: str = Field(
        ...,
        description=(
            "Clear step-by-step synthesis of fundamental analysis, technical analysis, "
            "market context, areas of agreement or conflict, and why this specific decision was chosen."
        ),
    )
    ft_summary: str = Field(
        ...,
        description=(
            "Concise 3-5 sentence summary capturing the key signals, confidence levels, "
            "and main driving factors from both fundamental and technical sub-agents."
        ),
    )
    entry_price: float = Field(
        ...,
        description="Recommended entry price for BUY or exit price for SELL. Usually use latest Close unless a better technical level is identified.",
    )
    risk_notes: str = Field(
        ...,
        description=(
            "Stop-loss level, position sizing considerations, key risk factors, "
            "and specific conditions that would invalidate this trade."
        ),
    )


class RiskReview(BaseModel):
    """Structured output from the risk manager node."""
    verdict: Literal["APPROVE", "FLAG", "REJECT"] = Field(
        ...,
        description="Risk judgment on the proposed trade.",
    )
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        ...,
        description="Overall risk classification of the proposed trade.",
    )
    confidence_adjustment: Optional[int] = Field(
        None, 
        ge=1, 
        le=100,
        description="Suggested new confidence level if verdict is APPROVE or FLAG (optional).",
    )
    critique: str = Field(
        ...,
        description=(
            "Detailed but concise explanation of risks, weaknesses, strengths, "
            "and clear justification for the verdict."
        ),
    )


class GraphState(TypedDict):
    """LangGraph state definition."""
    df: pd.DataFrame
    symbol: str
    run_timestamp: str | None
    live_snapshot: dict | None
    
    # Populated by nodes
    data_summary: str | None
    market_context: dict[str, Any] | None
    fundamental_analysis: SubAgentAnalysis | None
    technical_analysis: SubAgentAnalysis | None
    decision: AgentSchema | None
    raw_response: str | None
    risk_review: RiskReview | None