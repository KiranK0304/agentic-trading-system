from pathlib import Path
import pandas as pd
import logging
from typing import Callable, Union

from langchain_core.prompts import ChatPromptTemplate

from .schemas import GraphState, AgentSchema, SubAgentAnalysis, RiskReview
from utils.market_context import build_market_context_payload
from utils.technical_indicators import generate_technical_summary

PROJECT_ROOT = Path(__file__).resolve().parent.parent
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# Shared helpers
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


def _format_analysis(
    analysis: Union[SubAgentAnalysis, AgentSchema, None], 
    name: str = "Analysis"
) -> str:
    """Format SubAgentAnalysis or AgentSchema nicely for LLM prompts."""
    if not analysis:
        return f"No {name.lower()} available."

    # Handle both signal (sub-agents) and decision (orchestrator)
    signal = getattr(analysis, "signal", getattr(analysis, "decision", "UNKNOWN"))
    confidence = getattr(analysis, "confidence", 0)
    reasoning = getattr(
        analysis, 
        "analysis", 
        getattr(analysis, "reasoning", "No reasoning provided.")
    )
    key_factors = getattr(analysis, "key_factors", [])

    factors_str = ", ".join(key_factors) if key_factors else "None provided"

    return (
        f"Signal/Decision: {signal} (Confidence: {confidence}%)\n"
        f"Reasoning/Analysis: {reasoning}\n"
        f"Key Factors: {factors_str}"
    )


def _validate_required_keys(state: GraphState, required_keys: list[str], node_name: str) -> None:
    """Raise clear error if any required state key is missing."""
    missing = [k for k in required_keys if k not in state]
    if missing:
        raise ValueError(f"{node_name}: Missing required state keys: {missing}")


# ──────────────────────────────────────────────────────────
# Node 1: prepare_data_node
# ──────────────────────────────────────────────────────────

def prepare_data_node(state: GraphState) -> dict:
    """Prepare a clean text summary + recent candle table for the LLM."""
    _validate_required_keys(state, ["df", "symbol"], "prepare_data_node")

    df: pd.DataFrame = state["df"]

    if len(df) < 10:
        raise ValueError(f"Not enough data. Got only {len(df)} rows.")

    required_cols = ["Open", "High", "Low", "Close", "Volume", "Datetime_IST"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in dataframe: {missing_cols}")

    # Safe scalar extraction
    latest_close = df["Close"].iloc[-1].item()
    latest_high = df["High"].iloc[-1].item()
    latest_low = df["Low"].iloc[-1].item()
    avg_volume = int(df["Volume"].mean().item())

    start_time = df["Datetime_IST"].iloc[0]
    end_time = df["Datetime_IST"].iloc[-1]

    summary = f"""\
Symbol: {state["symbol"]}
Total 5-min bars: {len(df)}
Time range: {start_time} → {end_time}
Latest Close: ₹{latest_close:.2f}
Average Volume: {avg_volume:,}"""

    live = state.get("live_snapshot")
    if live:
        summary += f"""\n
--- LIVE SPOT SNAPSHOT ---
LTP: ₹{live.get('ltp', 'N/A')} (Day Change: {live.get('change', 'N/A')}, {live.get('pChange', 'N/A')}%)
Day Open: ₹{live.get('open')} | High: ₹{live.get('high')} | Low: ₹{live.get('low')}
Data Source: {live.get('source')}"""

    recent_data = (
        df.tail(25)[["Open", "High", "Low", "Close", "Volume"]]
        .round(2)
        .to_string(index=False)
    )

    # ── Fundamental context: price, volume, macro (NO technical indicators) ──
    fundamental_context = f"{summary}\n\nLast 25 candles:\n{recent_data}"

    # ── Technical context: everything above + computed indicators ──
    try:
        ta_summary = generate_technical_summary(df)
    except Exception as e:
        logger.warning(f"Failed to generate technical summary: {e}")
        ta_summary = f"Technical Indicators Error: {e}"

    data_summary = f"{summary}\n\n{ta_summary}\n\nLast 25 candles:\n{recent_data}"

    return {"data_summary": data_summary, "fundamental_context": fundamental_context}


# ──────────────────────────────────────────────────────────
# Node 2: market_context_node
# ──────────────────────────────────────────────────────────

def market_context_node(state: GraphState) -> dict:
    """Fetch global index levels, Fear & Greed, and general market headlines."""
    _validate_required_keys(state, ["symbol"], "market_context_node")

    market_context_data = build_market_context_payload(
        symbol_for_filename=state["symbol"],
    )
    return {"market_context": market_context_data}


# ──────────────────────────────────────────────────────────
# Node 3: Fundamental analysis sub-agent (factory)
# ──────────────────────────────────────────────────────────

def make_fundamental_node(
    llm_with_structured_output,
) -> Callable[[GraphState], dict]:
    """Factory: builds the fundamental-analysis node."""
    system_prompt = _load_prompt("fundamental_system_prompt.md")

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user",
         "Here is the data for fundamental analysis:\n\n"
         "{data_context}\n\n"
         "Global market context:\n{macro_context}\n\n"
         "Provide your fundamental analysis now."),
    ])

    def fundamental_node(state: GraphState) -> dict:
        """Run the fundamental analysis sub-agent."""
        chain = prompt_template | llm_with_structured_output
        try:
            result: SubAgentAnalysis = chain.invoke({
                "data_context": state.get("fundamental_context") or state.get("data_summary", "No data available."),
                "macro_context": _get_macro_context(state),
            })
        except Exception as e:
            logger.warning("Fundamental sub-agent parse failed; using safe fallback output: %s", e)
            result = SubAgentAnalysis(
                analysis=(
                    "Fundamental agent returned invalid structured output. "
                    "Falling back to a neutral signal to keep the pipeline running."
                ),
                signal="NEUTRAL",
                confidence=35,
                key_factors=["Structured output parse failure in fundamental sub-agent."],
             )
        return {"fundamental_analysis": result}

    return fundamental_node


# ──────────────────────────────────────────────────────────
# Node 4: Technical analysis sub-agent (factory)
# ──────────────────────────────────────────────────────────

def make_technical_node(
    llm_with_structured_output,
) -> Callable[[GraphState], dict]:
    """Factory: builds the technical-analysis node."""
    system_prompt = _load_prompt("technical_system_prompt.md")

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user",
         "Here is the 5-minute OHLCV data for technical analysis:\n\n"
         "{data_context}\n\n"
         "Global market context:\n{macro_context}\n\n"
         "Provide your technical analysis now."),
    ])

    def technical_node(state: GraphState) -> dict:
        """Run the technical analysis sub-agent."""
        chain = prompt_template | llm_with_structured_output
        try:
            result: SubAgentAnalysis = chain.invoke({
                "data_context": state.get("data_summary", "No data available."),
                "macro_context": _get_macro_context(state),
            })
        except Exception as e:
            logger.warning("Technical sub-agent parse failed; using safe fallback output: %s", e)
            result = SubAgentAnalysis(
                analysis=(
                    "Technical agent returned invalid structured output. "
                    "Falling back to a neutral signal to keep the pipeline running."
                ),
                signal="NEUTRAL",
                confidence=35,
                key_factors=["Structured output parse failure in technical sub-agent."],
            )
        return {"technical_analysis": result}

    return technical_node


# ──────────────────────────────────────────────────────────
# Node 5: Orchestrator — final decision-maker (factory)
# ──────────────────────────────────────────────────────────

def make_orchestrator_node(
    llm_with_structured_output,
    summary_dir: Path | None = None,
) -> Callable[[GraphState], dict]:
    """Factory: builds the orchestrator node with two-pass logic (initial + risk-aware)."""
    if summary_dir is None:
        summary_dir = PROJECT_ROOT / "Summary"

    system_prompt_1 = _load_prompt("orchestrator_1.md")
    system_prompt_2 = _load_prompt("orchestrator_2.md")

    # First pass: Full context for initial decision
    base_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_1),
        ("user",
         "Here is the complete analysis context for your final decision:\n\n"
         "## Raw Market Data\n{data_summary}\n\n"
         "## Global Market Context\n{macro_context}\n\n"
         "## Fundamental Analysis (Sub-Agent)\n{fundamental_analysis}\n\n"
         "## Technical Analysis (Sub-Agent)\n{technical_analysis}\n\n"
         "Synthesize all inputs and provide your final trading decision now."),
    ])

    # Second pass: Rich re-evaluation with full original context + risk critique
    risk_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_2),
        ("user",
         "You previously made a trading decision based on the following context:\n\n"
         "## Raw Market Data\n{data_summary}\n\n"
         "## Global Market Context\n{macro_context}\n\n"
         "## Fundamental Analysis\n{fundamental_analysis}\n\n"
         "## Technical Analysis\n{technical_analysis}\n\n"
         "## Your Original Decision\n{original_decision}\n\n"
         "## Risk Manager Critique\n{risk_review}\n\n"
         "Re-evaluate your decision considering both the original analyses and the risk critique.\n\n"
         "You may:\n"
         "- Keep the same decision\n"
         "- Adjust confidence level\n"
         "- Change the decision if the risk is unacceptable\n\n"
         "Provide your FINAL decision now."),
    ])

    def orchestrator_node(state: GraphState) -> dict:
        """Orchestrator node — handles both first and second (risk review) passes."""
        _validate_required_keys(state, ["run_timestamp"], "orchestrator_node")
        logger.info(f"Orchestrator running at: {state['run_timestamp']}")

        if state.get("risk_review") is None:
            # ── FIRST PASS: Initial Decision ──
            _validate_required_keys(state, ["data_summary", "symbol"], "orchestrator_node (first pass)")

            # Save summary with sanitized timestamp
            timestamp = str(state.get("run_timestamp", "unknown")).replace(":", "-").replace(" ", "_").replace(".", "-")
            summary_path = summary_dir / f"summary_{state.get('symbol', 'unknown')}_{timestamp}.txt"
            summary_path.parent.mkdir(parents=True, exist_ok=True)

            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(state.get("data_summary", ""))

            # Prepare formatted inputs
            data_summary = state.get("data_summary", "No data available.")
            macro_context = _get_macro_context(state)
            fund_text = _format_analysis(state.get("fundamental_analysis"), "Fundamental Analysis")
            tech_text = _format_analysis(state.get("technical_analysis"), "Technical Analysis")

            chain = base_prompt | llm_with_structured_output
            response: AgentSchema = chain.invoke({
                "data_summary": data_summary,
                "macro_context": macro_context,
                "fundamental_analysis": fund_text,
                "technical_analysis": tech_text,
            })

        else:
            # ── SECOND PASS: Risk-Aware Re-evaluation ──
            prev_decision: AgentSchema | None = state.get("decision")
            risk: RiskReview | None = state.get("risk_review")

            if prev_decision is None or risk is None:
                raise ValueError("Missing decision or risk_review for second pass")

            # Provide rich context for better re-evaluation
            data_summary = state.get("data_summary", "No data available.")
            macro_context = _get_macro_context(state)
            fund_text = _format_analysis(state.get("fundamental_analysis"), "Fundamental Analysis")
            tech_text = _format_analysis(state.get("technical_analysis"), "Technical Analysis")
            original_decision_text = _format_analysis(prev_decision, "Original Decision")

            chain = risk_prompt | llm_with_structured_output
            response: AgentSchema = chain.invoke({
                "data_summary": data_summary,
                "macro_context": macro_context,
                "fundamental_analysis": fund_text,
                "technical_analysis": tech_text,
                "original_decision": original_decision_text,
                "risk_review": risk.critique,
            })

        return {
            "decision": response,           # AgentSchema
            "raw_response": str(response),  # For logging/debugging
        }

    return orchestrator_node


# ──────────────────────────────────────────────────────────
# Node 6: Risk Manager
# ──────────────────────────────────────────────────────────

def make_risk_manager_node(
    llm_with_structured_output,
) -> Callable[[GraphState], dict]:
    """Factory: builds the risk-manager node."""
    system_prompt = _load_prompt("risk_manager_system_prompt.md")

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user",
         "Here is the orchestrator's trading decision:\n\n"
         "Decision: {decision}\n"
         "Confidence: {confidence}\n\n"
         "Reasoning:\n{reasoning}\n\n"
         "Evaluate the risk of this trade and provide a structured risk review."),
    ])

    def risk_manager_node(state: GraphState) -> dict:
        """Run the risk evaluation agent."""
        agent_output: AgentSchema | None = state.get("decision")
        if agent_output is None:
            raise ValueError("Missing orchestrator decision for risk evaluation")

        chain = prompt_template | llm_with_structured_output
        result: RiskReview = chain.invoke({
            "decision": agent_output.decision,
            "confidence": agent_output.confidence,
            "reasoning": agent_output.reasoning,
        })

        return {"risk_review": result}

    return risk_manager_node