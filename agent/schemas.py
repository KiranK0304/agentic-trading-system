from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, TypedDict, Any
import pandas as pd
import json


def _coerce_list(v):
    """Accept both a real list and a JSON-encoded string of a list."""
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        return [v]
    return v


class SubAgentAnalysis(BaseModel):
    """Structured output from fundamental or technical analysis sub-agents."""
    analysis: str = Field(
        default="No analysis provided.",
        description="Detailed analysis reasoning — cite specific data points, patterns, and observations from the provided data and market context.",
    )
    signal: Literal["BULLISH", "BEARISH", "NEUTRAL"] = Field(
        default="NEUTRAL",
        description="Clear directional signal based on the analysis.",
    )
    confidence: int = Field(
        default=50,
        ge=1, 
        le=100,
        description="Confidence in the signal (1-100). Be honest about uncertainty.",
    )
    key_factors: list[str] = Field(
        default_factory=list,
        description="Top 3-5 most important factors driving the signal. Each as a short, concise sentence.",
    )

    @field_validator("signal", mode="before")
    @classmethod
    def _normalize_signal(cls, v):
        if isinstance(v, str):
            normalized = v.strip().upper()
            if normalized in {"BULLISH", "BEARISH", "NEUTRAL"}:
                return normalized
        return "NEUTRAL"

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, v):
        try:
            if isinstance(v, str):
                v = v.strip()
            value = int(float(v))
        except (TypeError, ValueError):
            return 50
        if value < 1:
            return 1
        if value > 100:
            return 100
        return value

    @field_validator("key_factors", mode="before")
    @classmethod
    def _parse_key_factors(cls, v):
        parsed = _coerce_list(v)
        if parsed in (None, "", []):
            return ["No key factors provided by model output."]
        return parsed


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
    data_summary: str | None            # Full summary WITH technical indicators (for technical agent)
    fundamental_context: str | None     # Price/volume/macro only, NO technical indicators (for fundamental agent)
    market_context: dict[str, Any] | None
    fundamental_analysis: SubAgentAnalysis | None
    technical_analysis: SubAgentAnalysis | None
    decision: AgentSchema | None
    raw_response: str | None
    risk_review: RiskReview | None