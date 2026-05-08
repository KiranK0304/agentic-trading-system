"""
Scheduled background tasks for the virtual trading system.

- update_price_task: Runs every 5 minutes, fetches latest price, updates unrealized P&L.
- run_agent_task:    Runs every 30 minutes, runs the full agent pipeline,
                     extracts the decision, and executes a virtual trade.
"""

import logging
import concurrent.futures
from datetime import datetime

from utils.data_loader import get_live_info, get_historical_data
from agent.trading_agent import run_trading_agent

logger = logging.getLogger("tasks")

TARGET_ASSET = "NIFTY 50"

# Minimum confidence to actually execute a trade (adjustable)
MIN_CONFIDENCE = 50


def update_price_task(portfolio) -> None:
    """
    Fetch the latest price from Yahoo Finance / NSE and
    update the portfolio's unrealized P&L.

    Runs every 5 minutes via the scheduler.
    """
    logger.info("⏱  [5-min] Starting price update...")

    try:
        live = get_live_info(TARGET_ASSET)
        latest_price = live.get("ltp")

        if latest_price is None:
            logger.warning("⚠️  Could not fetch latest price — skipping update.")
            return

        unrealized = portfolio.update_price(float(latest_price))
        state = portfolio.get_state()
        logger.info(
            f"✅ [5-min] Price updated → ₹{latest_price:.2f}  |  "
            f"Position: {state['position']}  |  "
            f"Unrealized P&L: ₹{unrealized:+.2f}  |  "
            f"Capital: ₹{state['capital']:.2f}"
        )
    except Exception as e:
        logger.exception(f"❌ [5-min] Price update failed: {e}")


def run_agent_task(portfolio, last_run_results: dict) -> None:
    """
    Run the full LangGraph trading pipeline, extract the final
    decision, and execute a virtual trade in the portfolio.
    Also stores the full agent results so the frontend can display them.

    Runs every 30 minutes via the scheduler.
    """
    logger.info(f"⏱  [30-min] Starting agent run for {TARGET_ASSET}...")

    try:
        # 1. Fetch data concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_live = executor.submit(get_live_info, TARGET_ASSET)
            future_hist = executor.submit(
                get_historical_data, TARGET_ASSET, "5d", "5m"
            )
            live_snapshot = future_live.result()
            df = future_hist.result()

        if df.empty:
            logger.error("❌ [30-min] Historical data is empty — skipping agent run.")
            return

        # 2. Run the full agent pipeline and capture ALL results
        from agent.trading_agent import build_trading_graph
        from agent.schemas import GraphState

        agent = build_trading_graph()
        initial_state: GraphState = {
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

        result = agent.invoke(initial_state)
        decision = result["decision"]

        # 3. Serialize all agent outputs for the frontend
        def _serialize_analysis(obj):
            if obj is None:
                return None
            return {
                "signal": getattr(obj, "signal", "NEUTRAL"),
                "confidence": getattr(obj, "confidence", 50),
                "key_factors": getattr(obj, "key_factors", []),
                "analysis": getattr(obj, "analysis", ""),
            }

        def _serialize_risk(obj):
            if obj is None:
                return None
            return {
                "verdict": getattr(obj, "verdict", ""),
                "risk_level": getattr(obj, "risk_level", ""),
                "confidence_adjustment": getattr(obj, "confidence_adjustment", None),
                "critique": getattr(obj, "critique", ""),
            }

        def _serialize_decision(obj):
            if obj is None:
                return None
            return {
                "decision": getattr(obj, "decision", ""),
                "confidence": getattr(obj, "confidence", 50),
                "entry_price": getattr(obj, "entry_price", 0),
                "reasoning": getattr(obj, "reasoning", ""),
                "risk_notes": getattr(obj, "risk_notes", ""),
                "ft_summary": getattr(obj, "ft_summary", ""),
            }

        # Store results in the shared dict
        last_run_results.clear()
        last_run_results.update({
            "timestamp": datetime.now().isoformat(),
            "symbol": TARGET_ASSET,
            "fundamental": _serialize_analysis(result.get("fundamental_analysis")),
            "technical": _serialize_analysis(result.get("technical_analysis")),
            "risk_review": _serialize_risk(result.get("risk_review")),
            "decision": _serialize_decision(decision),
        })

        logger.info(
            f"📊 [30-min] Agent decision: {decision.decision} "
            f"(confidence {decision.confidence}%) at ₹{decision.entry_price:.2f}"
        )

        # 4. Execute trade in the virtual portfolio
        if decision.confidence >= MIN_CONFIDENCE:
            portfolio.execute_signal(
                signal=decision.decision,
                price=decision.entry_price,
                timestamp=datetime.now().isoformat(),
            )
            state = portfolio.get_state()
            logger.info(
                f"✅ [30-min] Trade executed → {decision.decision} at ₹{decision.entry_price:.2f}  |  "
                f"Position: {state['position']}  |  "
                f"Realized P&L: ₹{state['realized_pnl']:+.2f}  |  "
                f"Capital: ₹{state['capital']:.2f}"
            )
        else:
            logger.info(
                f"⚪ [30-min] Confidence {decision.confidence}% < {MIN_CONFIDENCE}% threshold — "
                f"skipping trade execution."
            )

    except Exception as e:
        logger.exception(f"❌ [30-min] Agent task failed: {e}")

