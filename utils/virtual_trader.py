"""
Virtual Trader for simulated trading with reinforcement learning models
"""

import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass

@dataclass
class VirtualTrade:
    """Represents a virtual trade"""
    symbol: str
    action: str  # "BUY" or "SELL"
    quantity: float
    entry_price: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    strategy: str = "RL_MODEL"
    confidence: float = 0.0
    risk_level: str = "MEDIUM"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "symbol": self.symbol,
            "action": self.action,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time.isoformat(),
            "exit_price": self.exit_price,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "strategy": self.strategy,
            "confidence": self.confidence,
            "risk_level": self.risk_level
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'VirtualTrade':
        """Create from dictionary"""
        return cls(
            symbol=data["symbol"],
            action=data["action"],
            quantity=data["quantity"],
            entry_price=data["entry_price"],
            entry_time=datetime.fromisoformat(data["entry_time"]),
            exit_price=data["exit_price"],
            exit_time=datetime.fromisoformat(data["exit_time"]) if data["exit_time"] else None,
            pnl=data["pnl"],
            pnl_pct=data["pnl_pct"],
            strategy=data["strategy"],
            confidence=data["confidence"],
            risk_level=data["risk_level"]
        )

class VirtualPortfolio:
    """Manages virtual portfolio state"""
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Dict] = {}  # symbol -> position info
        self.total_value = initial_capital
        self.history: List[Dict] = []  # Portfolio value history
        
    def add_position(self, symbol: str, quantity: float, price: float) -> bool:
        """Add a new position or add to existing position"""
        cost = quantity * price
        
        # Check if we have enough cash
        if cost > self.cash:
            return False
        
        # Update cash
        self.cash -= cost
        
        # Update position
        if symbol in self.positions:
            # Update existing position
            pos = self.positions[symbol]
            new_quantity = pos["quantity"] + quantity
            new_cost = pos["cost_basis"] + cost
            pos["quantity"] = new_quantity
            pos["cost_basis"] = new_cost
            pos["avg_price"] = new_cost / new_quantity
        else:
            # Create new position
            self.positions[symbol] = {
                "quantity": quantity,
                "cost_basis": cost,
                "avg_price": price,
                "current_price": price
            }
        
        # Update portfolio value
        self._update_portfolio_value()
        return True
    
    def reduce_position(self, symbol: str, quantity: float, price: float) -> Tuple[bool, float, float]:
        """Reduce or close a position"""
        if symbol not in self.positions:
            return False, 0, 0
        
        pos = self.positions[symbol]
        
        # Make sure we don't sell more than we have
        sell_quantity = min(quantity, pos["quantity"])
        
        # Calculate proceeds and P&L
        proceeds = sell_quantity * price
        cost_basis_per_share = pos["cost_basis"] / pos["quantity"]
        cost_basis_portion = sell_quantity * cost_basis_per_share
        pnl = proceeds - cost_basis_portion
        pnl_pct = (price / pos["avg_price"] - 1) * 100
        
        # Update cash
        self.cash += proceeds
        
        # Update position
        pos["quantity"] -= sell_quantity
        pos["cost_basis"] -= cost_basis_portion
        
        # Remove position if quantity is now 0
        if pos["quantity"] <= 0:
            del self.positions[symbol]
        
        # Update portfolio value
        self._update_portfolio_value()
        
        return True, pnl, pnl_pct
    
    def update_prices(self, prices: Dict[str, float]):
        """Update current prices for all positions"""
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol]["current_price"] = price
        
        self._update_portfolio_value()
    
    def _update_portfolio_value(self):
        """Update total portfolio value"""
        positions_value = sum(
            pos["quantity"] * pos["current_price"] 
            for pos in self.positions.values()
        )
        
        self.total_value = self.cash + positions_value
        
        # Add to history
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "cash": self.cash,
            "positions_value": positions_value,
            "total_value": self.total_value
        })
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position details for a symbol"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Dict]:
        """Get all positions"""
        return self.positions
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary"""
        positions_value = sum(
            pos["quantity"] * pos["current_price"] 
            for pos in self.positions.values()
        )
        
        return {
            "cash": self.cash,
            "positions_value": positions_value,
            "total_value": self.total_value,
            "total_return": (self.total_value / self.initial_capital - 1) * 100,
            "position_count": len(self.positions)
        }
    
    def to_dict(self) -> Dict:
        """Convert portfolio to dictionary for serialization"""
        return {
            "initial_capital": self.initial_capital,
            "cash": self.cash,
            "positions": {k: v for k, v in self.positions.items()},
            "total_value": self.total_value,
            "history": self.history
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'VirtualPortfolio':
        """Create portfolio from dictionary"""
        portfolio = cls(initial_capital=data["initial_capital"])
        portfolio.cash = data["cash"]
        portfolio.positions = data["positions"]
        portfolio.total_value = data["total_value"]
        portfolio.history = data["history"]
        return portfolio

class VirtualTrader:
    """
    Virtual trader for simulated trading with AI models
    """
    
    def __init__(self, data_dir: str = "data/virtual_trading"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
        self.portfolio = VirtualPortfolio()
        self.trades: List[VirtualTrade] = []
        self.active_trades: Dict[str, VirtualTrade] = {}  # symbol -> active trade
        
        # Load existing data if available
        self._load_data()
        
        # Set up logging
        self.logger = logging.getLogger("virtual_trader")
    
    def buy(self, 
           symbol: str, 
           price: float, 
           quantity: float, 
           strategy: str = "RL_MODEL",
           confidence: float = 0.0,
           risk_level: str = "MEDIUM") -> Optional[VirtualTrade]:
        """
        Execute a buy order
        
        Args:
            symbol: Stock/option symbol
            price: Current price
            quantity: Quantity to buy
            strategy: Strategy name
            confidence: Model confidence (0-1)
            risk_level: Risk level (LOW, MEDIUM, HIGH)
            
        Returns:
            VirtualTrade if successful, None otherwise
        """
        # Check if we already have an active trade for this symbol
        if symbol in self.active_trades:
            self.logger.warning(f"Already have an active trade for {symbol}")
            return None
        
        # Add position to portfolio
        success = self.portfolio.add_position(symbol, quantity, price)
        if not success:
            self.logger.warning(f"Failed to add position for {symbol} - insufficient funds")
            return None
        
        # Create trade object
        trade = VirtualTrade(
            symbol=symbol,
            action="BUY",
            quantity=quantity,
            entry_price=price,
            entry_time=datetime.now(),
            strategy=strategy,
            confidence=confidence,
            risk_level=risk_level
        )
        
        # Add to active trades
        self.active_trades[symbol] = trade
        
        # Save data
        self._save_data()
        
        return trade
    
    def sell(self, 
            symbol: str, 
            price: float, 
            quantity: Optional[float] = None) -> Optional[VirtualTrade]:
        """
        Execute a sell order
        
        Args:
            symbol: Stock/option symbol
            price: Current price
            quantity: Quantity to sell (None for all)
            
        Returns:
            Completed VirtualTrade if successful, None otherwise
        """
        # Check if we have an active trade for this symbol
        if symbol not in self.active_trades:
            # Check if we have a position for this symbol
            position = self.portfolio.get_position(symbol)
            if not position:
                self.logger.warning(f"No active trade or position for {symbol}")
                return None
                
            # Create a new trade to sell from
            trade = VirtualTrade(
                symbol=symbol,
                action="SELL",
                quantity=position["quantity"],
                entry_price=position["avg_price"],
                entry_time=datetime.now() 
            )
            self.active_trades[symbol] = trade
        
        # Get the active trade
        trade = self.active_trades[symbol]
        
        # Determine quantity to sell
        sell_quantity = quantity if quantity is not None else trade.quantity
        
        # Reduce position in portfolio
        success, pnl, pnl_pct = self.portfolio.reduce_position(symbol, sell_quantity, price)
        if not success:
            self.logger.warning(f"Failed to reduce position for {symbol}")
            return None
        
        # Update trade with exit information
        trade.exit_price = price
        trade.exit_time = datetime.now()
        trade.pnl = pnl
        trade.pnl_pct = pnl_pct
        
        # Move from active trades to completed trades
        del self.active_trades[symbol]
        self.trades.append(trade)
        
        # Save data
        self._save_data()
        
        return trade
    
    def update_prices(self, prices: Dict[str, float]):
        """Update current prices for portfolio"""
        self.portfolio.update_prices(prices)
        self._save_data()
    
    def get_active_trades(self) -> List[VirtualTrade]:
        """Get all active trades"""
        return list(self.active_trades.values())
    
    def get_completed_trades(self) -> List[VirtualTrade]:
        """Get all completed trades"""
        return self.trades
    
    def get_trade_history(self, symbol: Optional[str] = None) -> List[VirtualTrade]:
        """Get trade history for a symbol or all symbols"""
        if symbol:
            return [t for t in self.trades if t.symbol == symbol]
        return self.trades
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary"""
        return self.portfolio.get_portfolio_summary()
    
    def _save_data(self):
        """Save trader data to disk"""
        # Save portfolio
        portfolio_file = self.data_dir / "portfolio.json"
        with open(portfolio_file, "w") as f:
            json.dump(self.portfolio.to_dict(), f, indent=2)
        
        # Save active trades
        active_trades_file = self.data_dir / "active_trades.json"
        with open(active_trades_file, "w") as f:
            json.dump([t.to_dict() for t in self.active_trades.values()], f, indent=2)
        
        # Save completed trades
        trades_file = self.data_dir / "completed_trades.json"
        with open(trades_file, "w") as f:
            json.dump([t.to_dict() for t in self.trades], f, indent=2)
    
    def _load_data(self):
        """Load trader data from disk"""
        # Load portfolio
        portfolio_file = self.data_dir / "portfolio.json"
        if portfolio_file.exists():
            try:
                with open(portfolio_file, "r") as f:
                    self.portfolio = VirtualPortfolio.from_dict(json.load(f))
            except Exception as e:
                self.logger.error(f"Failed to load portfolio: {e}")
        
        # Load active trades
        active_trades_file = self.data_dir / "active_trades.json"
        if active_trades_file.exists():
            try:
                with open(active_trades_file, "r") as f:
                    trades_data = json.load(f)
                    for trade_data in trades_data:
                        trade = VirtualTrade.from_dict(trade_data)
                        self.active_trades[trade.symbol] = trade
            except Exception as e:
                self.logger.error(f"Failed to load active trades: {e}")
        
        # Load completed trades
        trades_file = self.data_dir / "completed_trades.json"
        if trades_file.exists():
            try:
                with open(trades_file, "r") as f:
                    trades_data = json.load(f)
                    for trade_data in trades_data:
                        self.trades.append(VirtualTrade.from_dict(trade_data))
            except Exception as e:
                self.logger.error(f"Failed to load completed trades: {e}")
    
    def get_performance_metrics(self) -> Dict:
        """Calculate performance metrics"""
        if not self.trades:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "avg_profit": 0,
                "avg_loss": 0,
                "profit_factor": 0,
                "total_pnl": 0
            }
        
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl and t.pnl < 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        avg_profit = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([abs(t.pnl) for t in losing_trades]) if losing_trades else 0
        
        total_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
        total_loss = sum(abs(t.pnl) for t in losing_trades) if losing_trades else 0
        
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        return {
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "avg_profit": avg_profit,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "total_pnl": total_profit - total_loss,
            "sharpe_ratio": self._calculate_sharpe_ratio()
        }
    
    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.01) -> float:
        """Calculate Sharpe ratio from portfolio history"""
        if len(self.portfolio.history) < 2:
            return 0
        
        # Get daily returns
        values = []
        for entry in self.portfolio.history:
            try:
                values.append(entry["total_value"])
            except (KeyError, TypeError):
                continue
        
        if len(values) < 2:
            return 0
        
        returns = [(values[i] / values[i-1] - 1) for i in range(1, len(values))]
        
        # Compute annualized Sharpe ratio
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0
            
        # Assuming daily returns, annualize
        sharpe = (mean_return - risk_free_rate / 252) / std_return * np.sqrt(252)
        
        return sharpe

# Create a singleton instance
virtual_trader = VirtualTrader() 