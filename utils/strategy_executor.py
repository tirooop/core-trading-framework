from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import os
import logging
import sys
from pathlib import Path
import time
import threading
import queue

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from data.databento_downloader import download as yf_download
from utils.ai_analyst_v2 import AIAnalyst
from utils.strategy_validator import StrategyValidator
from utils.signal_fusion import SignalFusionEngine
from utils.unified_notifier import UnifiedNotifier, NotificationConfig
from utils.notifier_dispatcher import NotifierDispatcher
from utils.ai_judger import AIJudger
from utils.deepseek_client import DeepSeekClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("strategy_executor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("StrategyExecutor")

class Signal:
    """Class to hold signal data"""
    def __init__(self, 
                 symbol: str, 
                 action: str, 
                 confidence: float, 
                 timestamp: datetime,
                 risk_level: str = "MEDIUM",
                 final_score: float = 0.0,
                 reasoning: str = "",
                 recommendation: str = "",
                 strategy_type: str = ""):
        self.symbol = symbol
        self.action = action  # BUY, SELL, HOLD
        self.confidence = confidence
        self.timestamp = timestamp
        self.risk_level = risk_level
        self.final_score = final_score
        self.reasoning = reasoning
        self.recommendation = recommendation
        self.strategy_type = strategy_type
        
    def to_dict(self):
        return {
            "symbol": self.symbol,
            "action": self.action,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "risk_level": self.risk_level,
            "final_score": self.final_score,
            "reasoning": self.reasoning,
            "recommendation": self.recommendation,
            "strategy_type": self.strategy_type
        }

class StrategyExecutor:
    """Main class for executing AI option trading strategies"""
    
    def __init__(self, 
                 symbols: List[str] = None,
                 interval: int = 300,  # 5 minutes
                 min_confidence: float = 0.7,
                 risk_levels: Dict[str, float] = None,
                 notification_config: NotificationConfig = None,
                 use_ai_judger: bool = False,
                 deepseek_api_key: str = None):
        """
        Initialize the strategy executor.
        
        Args:
            symbols: List of symbols to analyze
            interval: Interval between analyses in seconds
            min_confidence: Minimum confidence threshold for signals
            risk_levels: Dictionary of risk levels and their thresholds
            notification_config: Configuration for notifications
            use_ai_judger: Whether to use AI judger for final decision
            deepseek_api_key: DeepSeek API key for AI judger
        """
        self.symbols = symbols or ["SPY", "QQQ", "AAPL", "MSFT"]
        self.interval = interval
        self.min_confidence = min_confidence
        self.risk_levels = risk_levels or {
            "LOW": 0.3,
            "MEDIUM": 0.6,
            "HIGH": 1.0
        }
        self.use_ai_judger = use_ai_judger
        
        # Initialize notification system
        self.notifier = UnifiedNotifier(config=notification_config)
        
        # Create the notifier dispatcher
        self.notifier_dispatcher = NotifierDispatcher(self.notifier)
        
        # Initialize components with notifier_dispatcher
        self.ai_analyst = AIAnalyst(notifier_dispatcher=self.notifier_dispatcher)
        self.strategy_validator = StrategyValidator()
        self.signal_fusion = SignalFusionEngine()
        
        # Initialize AI judger if enabled
        if self.use_ai_judger:
            deepseek_client = DeepSeekClient(api_key=deepseek_api_key)
            self.ai_judger = AIJudger(deepseek_client=deepseek_client)
        else:
            self.ai_judger = None
        
        # Signal management
        self.signal_history = {}  # Symbol -> list of signals
        self.signal_queue = queue.Queue()
        
        # Daily signals for reporting
        self.daily_signals = []
        self.last_report_time = datetime.now()
        
        # Thread control
        self.running = False
        self.worker_thread = None
    
    def start(self):
        """Start the strategy executor"""
        if self.running:
            logger.warning("Strategy executor is already running")
            return
            
        self.running = True
        self.worker_thread = threading.Thread(target=self._run_loop)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        logger.info("Strategy executor started")
    
    def stop(self):
        """Stop the strategy executor"""
        if not self.running:
            logger.warning("Strategy executor is not running")
            return
            
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        logger.info("Strategy executor stopped")
    
    def _run_loop(self):
        """Main execution loop"""
        while self.running:
            try:
                # Process each symbol
                for symbol in self.symbols:
                    try:
                        result = self.execute_strategy(symbol)
                        
                        # Add to queue for further processing
                        if result and result.get("status") == "success":
                            self.signal_queue.put(result)
                            
                    except Exception as e:
                        logger.error(f"Error executing strategy for {symbol}: {str(e)}")
                
                # Process any pending signals in the queue
                self._process_signal_queue()
                
                # Check if it's time to send daily report (at end of day)
                current_time = datetime.now()
                if (current_time.hour >= 16 and self.last_report_time.day != current_time.day) or \
                   (current_time - self.last_report_time).total_seconds() > 86400:  # 24 hours
                    self._send_daily_report()
                    self.last_report_time = current_time
                
                # Sleep until next interval
                time.sleep(self.interval)
                
            except Exception as e:
                logger.error(f"Error in strategy execution loop: {str(e)}")
                time.sleep(10)  # Sleep for a while before retrying
    
    def _process_signal_queue(self):
        """Process signals in the queue"""
        while not self.signal_queue.empty():
            try:
                signal_data = self.signal_queue.get(block=False)
                symbol = signal_data.get("symbol")
                signal = signal_data.get("signal")
                
                if symbol and signal:
                    # Store in history
                    if symbol not in self.signal_history:
                        self.signal_history[symbol] = []
                    
                    # Convert signal to Signal object if it's a dict
                    if isinstance(signal, dict):
                        signal_obj = Signal(
                            symbol=symbol,
                            action=signal.get("action", "HOLD"),
                            confidence=signal.get("confidence", 0.0),
                            timestamp=datetime.fromisoformat(signal.get("timestamp")),
                            risk_level=signal.get("risk_level", "MEDIUM"),
                            final_score=signal.get("final_score", 0.0),
                            reasoning=signal.get("reasoning", ""),
                            recommendation=signal.get("recommendation", ""),
                            strategy_type=signal.get("strategy_type", "")
                        )
                        self.signal_history[symbol].append(signal_obj)
                        
                        # Add to daily signals list for reporting
                        self.daily_signals.append(signal_obj.to_dict())
                    else:
                        self.signal_history[symbol].append(signal)
                
                # Prepare signal for dispatcher
                if isinstance(signal, dict) and signal.get("confidence", 0) >= self.min_confidence:
                    dispatch_data = {
                        "type": "entry" if signal.get("action") == "BUY" else "exit" if signal.get("action") == "SELL" else "hold",
                        "symbol": symbol,
                        "strategy": signal.get("strategy_type", "AI Strategy"),
                        "direction": "BULLISH" if signal.get("action") == "BUY" else "BEARISH" if signal.get("action") == "SELL" else "NEUTRAL",
                        "confidence": signal.get("confidence", 0),
                        "price": self._get_current_price(symbol),
                        "rr_ratio": signal.get("final_score", 0) * 2,  # Simple estimation
                        "ai_insight": signal.get("reasoning", ""),
                        "llm_analysis": signal_data.get("analysis", {}).get("llm_analysis", {})
                    }
                    
                    # Use the dispatcher for intelligent notifications
                    self.notifier_dispatcher.dispatch_signal(dispatch_data)
                
                self.signal_queue.task_done()
                
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error processing signal: {str(e)}")
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        try:
            data = yf_download(symbol, period="1d", interval="1m")
            if not data.empty:
                return data.iloc[-1]['Close']
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {str(e)}")
        return 0.0
    
    def _send_daily_report(self):
        """Send daily report of all signals"""
        if not self.daily_signals:
            logger.info("No signals to report today")
            return
            
        # Get simple performance metrics
        performance = self._calculate_performance()
        
        # Send the daily report
        self.notifier_dispatcher.send_daily_report(self.daily_signals, performance)
        
        # Reset daily signals list
        self.daily_signals = []
        logger.info("Sent daily report")
    
    def _calculate_performance(self) -> Dict[str, float]:
        """Calculate simple performance metrics"""
        # This is a placeholder, in a real system you would calculate actual P&L
        return {
            "daily_pnl": 0.0,
            "weekly_pnl": 0.0,
            "monthly_pnl": 0.0
        }
    
    def execute_strategy(self, symbol: str) -> Dict[str, Any]:
        """
        Execute trading strategy for a symbol
        
        Args:
            symbol: Stock symbol to analyze
            
        Returns:
            Dictionary with execution result
        """
        try:
            # Get market data
            df = self._get_market_data(symbol)
            if df is None or len(df) < 20:
                return {"status": "error", "message": f"Insufficient data for {symbol}"}
                
            # Current market price
            current_price = self._get_current_price(symbol)
            
            # Run AI analysis
            analysis_result = self.ai_analyst.analyze_symbol(
                symbol=symbol,
                data=df,
                current_price=current_price
            )
            
            # Get strategy result
            strategy_result = analysis_result.get("strategy_result", {})
            
            # Extract key metrics for signal
            confidence = strategy_result.get("confidence", 0.0)
            action = strategy_result.get("action", "HOLD")
            risk_level = strategy_result.get("risk_level", "MEDIUM")
            target_price = strategy_result.get("target_price", current_price * 1.05)
            stop_loss = strategy_result.get("stop_loss", current_price * 0.95)
            
            # Calculate risk-reward ratio
            risk = abs(current_price - stop_loss)
            reward = abs(target_price - current_price)
            risk_reward = reward / risk if risk > 0 else 0
            
            # Build signal context
            signal_context = {
                "symbol": symbol,
                "current_price": current_price,
                "target_price": target_price,
                "stop_loss": stop_loss,
                "risk_reward": risk_reward,
                "confidence": confidence,
                "sector_performance": strategy_result.get("sector_performance", 0.0),
                "option_flow": strategy_result.get("option_flow", "中性"),
                "direction": action,
                "strategy": strategy_result.get("strategy", "AI分析")
            }
            
            # If AI judger is enabled, use it to make final decision
            if self.use_ai_judger and self.ai_judger:
                # Get AI judgment
                ai_judgment = self.ai_judger.judge(signal_context)
                
                # Format the final result
                result = self.ai_judger.get_formatted_result(ai_judgment, signal_context)
                
                # If AI decides to notify, dispatch to notification system
                if result.get("notify") == "是":
                    self.notifier_dispatcher.send_option_entry_signal(
                        symbol=symbol,
                        option_type=result.get("option_type", "call"),
                        strike_price=target_price,
                        expiry_date=datetime.now() + timedelta(days=30),
                        current_price=current_price,
                        implied_volatility=strategy_result.get("implied_volatility", 0.3),
                        pressure_points={"support": stop_loss, "resistance": target_price},
                        risk_reward_ratio=risk_reward,
                        confidence_score=confidence,
                        analysis=result.get("reason", "AI推荐交易信号")
                    )
            else:
                # Traditional approach: Create signal if confidence exceeds threshold
                if confidence >= self.min_confidence:
                    signal = Signal(
                        symbol=symbol,
                        action=action,
                        confidence=confidence,
                        timestamp=datetime.now(),
                        risk_level=risk_level,
                        final_score=confidence,
                        reasoning=strategy_result.get("reasoning", ""),
                        recommendation=strategy_result.get("recommendation", ""),
                        strategy_type=strategy_result.get("strategy", "AI")
                    )
                    
                    # Add to result
                    result = {
                        "status": "success",
                        "symbol": symbol,
                        "signal": signal.to_dict(),
                        "analysis": analysis_result,
                        "strategy_result": strategy_result
                    }
                else:
                    # No signal generated
                    result = {
                        "status": "no_signal",
                        "symbol": symbol,
                        "reason": "Confidence below threshold",
                        "confidence": confidence,
                        "threshold": self.min_confidence
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in execute_strategy for {symbol}: {str(e)}")
            return {"status": "error", "message": str(e), "symbol": symbol}
    
    def _get_market_data(self, symbol: str) -> pd.DataFrame:
        """
        Get market data for a symbol.
        
        Args:
            symbol: The ticker symbol
            
        Returns:
            DataFrame containing market data
        """
        try:
            # Get data for multiple timeframes
            data_1d = yf_download(symbol, period="1y", interval="1d")
            data_1h = yf_download(symbol, period="60d", interval="1h") 
            data_5m = yf_download(symbol, period="5d", interval="5m")
            
            # Use daily data as the base
            if data_1d.empty:
                logger.warning(f"No daily data available for {symbol}")
                return None
                
            # Add technical indicators
            data = data_1d.copy()
            
            # Add basic indicators
            data['SMA_20'] = data['Close'].rolling(window=20).mean()
            data['SMA_50'] = data['Close'].rolling(window=50).mean()
            data['SMA_200'] = data['Close'].rolling(window=200).mean()
            
            # RSI
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            data['RSI'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = data['Close'].ewm(span=12, adjust=False).mean()
            exp2 = data['Close'].ewm(span=26, adjust=False).mean()
            data['MACD'] = exp1 - exp2
            data['MACD_Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
            
            # Bollinger Bands
            data['BB_Middle'] = data['Close'].rolling(window=20).mean()
            data['BB_StdDev'] = data['Close'].rolling(window=20).std()
            data['BB_Upper'] = data['BB_Middle'] + (data['BB_StdDev'] * 2)
            data['BB_Lower'] = data['BB_Middle'] - (data['BB_StdDev'] * 2)
            
            # Add volatility measure
            data['Volatility'] = data['Close'].rolling(window=20).std() / data['Close'].rolling(window=20).mean()
            
            # Store data from different timeframes in the metadata
            data.attrs['data_1h'] = data_1h
            data.attrs['data_5m'] = data_5m
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {str(e)}")
            return None
    
    def batch_execute(self, symbols: List[str] = None) -> Dict[str, Any]:
        """
        Execute strategies for multiple symbols.
        
        Args:
            symbols: List of symbols to analyze
            
        Returns:
            Dict of symbol -> result
        """
        results = {}
        symbols = symbols or self.symbols
        
        for symbol in symbols:
            try:
                result = self.execute_strategy(symbol)
                results[symbol] = result
                
                # Add to queue for processing
                if result and result.get("status") == "success":
                    self.signal_queue.put(result)
                    
            except Exception as e:
                logger.error(f"Error in batch execution for {symbol}: {str(e)}")
                results[symbol] = {"status": "error", "message": str(e)}
        
        # Process any signals generated
        self._process_signal_queue()
        
        return results
    
    def set_strategy_preset(self, preset_name: str) -> bool:
        """Set strategy preset for AI analysis"""
        return self.ai_analyst.set_strategy_preset(preset_name)
    
    def get_recent_signals(self, symbol: str, count: int = 20) -> List[Signal]:
        """
        Get recent signals for a symbol.
        
        Args:
            symbol: The ticker symbol
            count: Maximum number of signals to return
            
        Returns:
            List of recent signals
        """
        if symbol not in self.signal_history:
            return []
            
        # Return most recent signals first
        signals = sorted(
            self.signal_history[symbol], 
            key=lambda x: x.timestamp, 
            reverse=True
        )
        return signals[:count]
    
    def get_signal_queue_size(self) -> int:
        """Get the current size of the signal queue"""
        return self.signal_queue.qsize()
    
    def save_signals(self, output_path: str = "data/signals.json"):
        """Save all signals to a JSON file"""
        data = {}
        for symbol, signals in self.signal_history.items():
            data[symbol] = [signal.to_dict() for signal in signals]
            
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {sum(len(signals) for signals in self.signal_history.values())} signals to {output_path}")
    
    def load_signals(self, input_path: str = "data/signals.json"):
        """Load signals from a JSON file"""
        if not os.path.exists(input_path):
            logger.warning(f"Signal file {input_path} not found")
            return
            
        with open(input_path, 'r') as f:
            data = json.load(f)
            
        for symbol, signal_dicts in data.items():
            self.signal_history[symbol] = []
            for signal_dict in signal_dicts:
                signal = Signal(
                    symbol=signal_dict["symbol"],
                    action=signal_dict["action"],
                    confidence=signal_dict["confidence"],
                    timestamp=datetime.fromisoformat(signal_dict["timestamp"]),
                    risk_level=signal_dict.get("risk_level", "MEDIUM"),
                    final_score=signal_dict.get("final_score", 0.0),
                    reasoning=signal_dict.get("reasoning", ""),
                    recommendation=signal_dict.get("recommendation", ""),
                    strategy_type=signal_dict.get("strategy_type", "")
                )
                self.signal_history[symbol].append(signal)
                
        logger.info(f"Loaded {sum(len(signals) for signals in self.signal_history.values())} signals from {input_path}")
    
    def set_ai_judger(self, enabled: bool, api_key: str = None) -> bool:
        """
        Enable or disable the AI judger component
        
        Args:
            enabled: Whether to enable AI judger
            api_key: DeepSeek API key (optional)
            
        Returns:
            Success status
        """
        try:
            self.use_ai_judger = enabled
            
            if enabled:
                # Initialize AI judger with DeepSeek client
                deepseek_client = DeepSeekClient(api_key=api_key)
                self.ai_judger = AIJudger(deepseek_client=deepseek_client)
                logger.info("AI judger enabled")
            else:
                self.ai_judger = None
                logger.info("AI judger disabled")
                
            return True
        except Exception as e:
            logger.error(f"Error setting AI judger: {str(e)}")
            return False

if __name__ == "__main__":
    # 测试代码
    executor = StrategyExecutor()
    
    # 执行策略
    result = executor.execute_strategy("AAPL")
    
    # 输出结果
    print(json.dumps(result, indent=2, ensure_ascii=False)) 