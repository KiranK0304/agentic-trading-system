from pydantic import BaseModel, Field
from typing import Literal

class TradingDecision(BaseModel):
    """Structured output from the trading agent."""
    decision: Literal["BUY", "SELL", "HOLD"] = Field(
        ..., 
        description="Final trading decision: BUY, SELL, or HOLD"
    )
    confidence: int = Field(
        ..., 
        ge=1, 
        le=100, 
        description="Confidence score (1-100) in the decision"
    )
    reasoning: str = Field(
        ..., 
        description="Detailed step-by-step reasoning based ONLY on the provided price data. Include key observations from price action, trends, and any calculated indicators."
    )
    entry_price: float = Field(
        ..., 
        description="Recommended entry/exit price (use the latest Close price unless specified otherwise)"
    )
    risk_notes: str = Field(
        ..., 
        description="Key risks, stop-loss suggestion, or important caveats"
    )