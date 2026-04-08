from pydantic import BaseModel, Field
from typing import Literal

from typing import TypedDict, Annotated
import pandas as pd



class AgentSchema(BaseModel):
    """Structured output from the trading agent."""
    decision: Literal["BUY", "SELL"] = Field(..., description="Final trading decision: BUY, SELL")
    confidence: int = Field(..., ge=1, le=100, description="Confidence score (1-100) in the decision")
    reasoning: str = Field(..., description="Detailed step-by-step reasoning based ONLY on the provided price data. Include key observations from price action, trends, and any calculated indicators.")
    entry_price: float = Field(..., description="Recommended entry/exit price (use the latest Close price unless specified otherwise)")
    risk_notes: str = Field(..., description="Key risks, stop-loss suggestion, or important caveats")


fundamentals = {
    "source": str | None,           # path to Screener export (xlsx) or JSON
    "qualitative_view": str | None, # LLM’s analysis text
    "alignment_with_price_action": str | None,  # optional, also from LLM
}


class GraphState(TypedDict):
    df: pd.DataFrame
    symbol: str
    data_summary: str | None
    decision: AgentSchema | None
    raw_response: str | None
    max_iterations: Annotated[int, lambda x, y: x + y]
    fundamentals: dict | None