from typing import Literal, List, Dict, Any
from datetime import datetime

class VirtualPortfolio:
    """
    Tracks the state of a paper trading portfolio.
    Currently entirely in-memory for demonstration, but designed
    to be easily backed by a PostgreSQL database later.
    """
    def __init__(self, initial_capital: float = 1000000.0, lot_size: int = 25):
        self.initial_capital = initial_capital
        self.lot_size = lot_size
        
        # Current State
        self.capital = initial_capital
        self.position: Literal["LONG", "SHORT", "NEUTRAL"] = "NEUTRAL"
        self.entry_price: float = 0.0
        self.entry_time: str | None = None
        self.current_price: float = 0.0
        
        # PnL Tracking
        self.realized_pnl: float = 0.0
        self.unrealized_pnl: float = 0.0
        
        # History
        self.trade_history: List[Dict[str, Any]] = []

    def update_price(self, latest_price: float) -> float:
        """
        Updates the current known price and recalculates the unrealized PnL.
        Called every 5 minutes by the scheduler.
        """
        self.current_price = latest_price
        
        if self.position == "LONG":
            self.unrealized_pnl = (self.current_price - self.entry_price) * self.lot_size
        elif self.position == "SHORT":
            self.unrealized_pnl = (self.entry_price - self.current_price) * self.lot_size
        else:
            self.unrealized_pnl = 0.0
            
        return self.unrealized_pnl

    def execute_signal(self, signal: Literal["BUY", "SELL"], price: float, timestamp: str = None) -> None:
        """
        Executes a trade based on the agent's signal.
        For simplicity:
        - "BUY" means we want to be LONG.
        - "SELL" means we want to be SHORT.
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()
            
        self.current_price = price

        if signal == "BUY":
            if self.position == "LONG":
                pass # Already LONG, do nothing
            elif self.position == "SHORT":
                # Close SHORT, open LONG
                self._close_position(price, timestamp, reason="Reverse to LONG")
                self._open_position("LONG", price, timestamp)
            elif self.position == "NEUTRAL":
                self._open_position("LONG", price, timestamp)

        elif signal == "SELL":
            if self.position == "SHORT":
                pass # Already SHORT, do nothing
            elif self.position == "LONG":
                # Close LONG, open SHORT
                self._close_position(price, timestamp, reason="Reverse to SHORT")
                self._open_position("SHORT", price, timestamp)
            elif self.position == "NEUTRAL":
                self._open_position("SHORT", price, timestamp)

    def _open_position(self, direction: Literal["LONG", "SHORT"], price: float, timestamp: str):
        """Internal helper to open a position."""
        self.position = direction
        self.entry_price = price
        self.entry_time = timestamp
        self.unrealized_pnl = 0.0

    def _close_position(self, price: float, timestamp: str, reason: str = "Signal Reversal"):
        """Internal helper to close a position and book PnL."""
        # Calculate final PnL for this trade
        if self.position == "LONG":
            trade_pnl = (price - self.entry_price) * self.lot_size
        elif self.position == "SHORT":
            trade_pnl = (self.entry_price - price) * self.lot_size
        else:
            trade_pnl = 0.0
            
        # Update capital and realized PnL
        self.realized_pnl += trade_pnl
        self.capital += trade_pnl
        
        # Record trade in history
        self.trade_history.append({
            "direction": self.position,
            "entry_time": self.entry_time,
            "entry_price": self.entry_price,
            "exit_time": timestamp,
            "exit_price": price,
            "pnl": trade_pnl,
            "reason": reason
        })
        
        # Reset state
        self.position = "NEUTRAL"
        self.entry_price = 0.0
        self.entry_time = None
        self.unrealized_pnl = 0.0

    def get_state(self) -> Dict[str, Any]:
        """Returns the current portfolio snapshot for the frontend."""
        return {
            "capital": self.capital,
            "position": self.position,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "total_value": self.capital + self.unrealized_pnl
        }
