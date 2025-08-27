"""
Trading Integration module to connect virtual trader, RL model, and notification systems.
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
import pandas as pd
import numpy as np
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_integration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("trading_integration")

# Import project modules
import sys
sys.path.append('.')

from utils.virtual_trader import virtual_trader
from utils.telegram_notifier import TelegramNotifier
from model.dqn_agent import DQNAgent
from risk.advanced_risk_manager import create_risk_manager

class TradingIntegration:
    """
    Integration layer between RL models, virtual trader, and notification systems.
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize the integration layer.
        
        Args:
            config_path: Path to the config file
        """
        self.config_path = config_path
        self.rl_agent = None
        self.risk_manager = None
        self.telegram_notifier = None
        
        # Load components
        self._load_components()
        
        # Store prediction history
        self.prediction_history = {}  # symbol -> list of predictions
        
        # Trading signals directory
        self.signals_dir = Path("data/signals")
        self.signals_dir.mkdir(exist_ok=True, parents=True)
        
        logger.info("Trading integration initialized")
    
    def _load_components(self):
        """Load all required components"""
        try:
            # Initialize DQN agent
            state_dim = 124  # Example: 10 lookback * 12 features + 4 Greeks
            action_dim = 3   # No action, Buy, Sell
            self.rl_agent = DQNAgent(state_dim, action_dim)
            
            # Try to load saved model, or use untrained model if not available
            model_path = "data/models/dqn_options.h5"
            if os.path.exists(model_path):
                self.rl_agent.load_model()
                logger.info("Loaded pre-trained RL model")
            else:
                logger.warning("Using untrained RL model (model file not found)")
            
            # Initialize risk manager
            self.risk_manager = create_risk_manager()
            logger.info("Initialized risk manager")
            
            # Setup Telegram notifier
            self.telegram_notifier = TelegramNotifier()
            
            logger.info("All components loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error loading components: {str(e)}")
            return False
    
    def get_market_data(self, symbol: str) -> pd.DataFrame:
        """
        Get market data for a symbol.
        In a real implementation, this would fetch from your market data module.
        
        Args:
            symbol: The stock/option symbol
            
        Returns:
            DataFrame with market data
        """
        # Placeholder - in real implementation, get from market data module
        # This is simplified sample data for testing
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        
        np.random.seed(42)  # For reproducibility
        close = 100 + np.cumsum(np.random.normal(0, 1, 30))
        
        data = pd.DataFrame({
            'date': dates,
            'open': close * (1 + np.random.normal(0, 0.01, 30)),
            'high': close * (1 + np.random.normal(0, 0.02, 30)),
            'low': close * (1 - np.random.normal(0, 0.02, 30)),
            'close': close,
            'volume': np.random.randint(1000, 5000, 30)
        })
        
        # Add some technical indicators
        data['sma20'] = data['close'].rolling(window=20).mean()
        data['rsi'] = self._calculate_rsi(data['close'])
        
        return data
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI technical indicator"""
        delta = prices.diff()
        
        up = delta.copy()
        up[up < 0] = 0
        down = -delta.copy()
        down[down < 0] = 0
        
        avg_gain = up.rolling(window=period).mean()
        avg_loss = down.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def get_option_data(self, symbol: str) -> Dict:
        """
        Get option data for a symbol.
        In a real implementation, this would fetch from your options data source.
        
        Args:
            symbol: The stock symbol
            
        Returns:
            Dictionary with option data for closest ATM call
        """
        # Placeholder - in real implementation, get from options data source
        data = self.get_market_data(symbol)
        current_price = data['close'].iloc[-1]
        
        # Simulate option data (closest ATM call)
        option_data = {
            'symbol': f"{symbol}C{current_price:.0f}",
            'underlying': symbol,
            'strike': round(current_price / 5) * 5,  # Round to nearest 5
            'expiry': (datetime.now() + pd.Timedelta(days=30)).strftime('%Y-%m-%d'),
            'option_type': 'call',
            'price': current_price * 0.05,  # Approximate option price
            'delta': 0.5,  # ATM delta
            'gamma': 0.05,
            'theta': -0.2,
            'vega': 0.8,
            'volume': 500,
            'open_interest': 1000
        }
        
        return option_data
    
    def preprocess_for_rl(self, market_data: pd.DataFrame, option_data: Dict) -> np.ndarray:
        """
        Preprocess market and option data for RL model input.
        
        Args:
            market_data: DataFrame with market data
            option_data: Dictionary with option data
            
        Returns:
            Numpy array with state representation for RL model
        """
        # Extract relevant market features
        features = market_data.copy()
        
        # Calculate returns
        features['returns'] = features['close'].pct_change().fillna(0)
        
        # Volatility (10-day rolling std)
        features['volatility'] = features['close'].rolling(window=10).std().fillna(method='bfill')
        
        # Market trend
        features['trend'] = (features['close'] > features['sma20']).astype(int) * 2 - 1
        
        # Select feature columns
        feature_cols = ['returns', 'volatility', 'rsi', 'trend']
        
        # Create state representation - last 10 days of each feature
        lookback = 10
        state_data = []
        
        for col in feature_cols:
            state_data.extend(features[col].iloc[-lookback:].values)
        
        # Add option Greeks
        greeks = np.array([
            option_data['delta'],
            option_data['gamma'],
            option_data['theta'],
            option_data['vega']
        ])
        
        # Combine market features and Greeks
        state = np.concatenate([np.array(state_data), greeks])
        
        return state
    
    def get_prediction(self, symbol: str) -> Dict:
        """
        Get prediction from RL model for a symbol.
        
        Args:
            symbol: The stock/option symbol
            
        Returns:
            Dictionary with prediction results
        """
        try:
            # Get market and option data
            market_data = self.get_market_data(symbol)
            option_data = self.get_option_data(symbol)
            
            # Preprocess data for RL model
            state = self.preprocess_for_rl(market_data, option_data)
            
            # Get prediction from RL model
            # ai_score range [0, 1] (0 = not confident, 1 = very confident)
            ai_score = 0.8  # Placeholder for actual AI score calculation
            action_id = self.rl_agent.act(state, ai_score=ai_score, explore=False)
            
            # Convert action to human-readable format
            action_name = "NO_ACTION"
            if action_id == 1:
                action_name = "BUY"
            elif action_id == 2:
                action_name = "SELL"
            
            # Get confidence from model (placeholder)
            confidence = 0.8
            
            # Get risk assessment
            risk_assessment = self.risk_manager.check_portfolio_risk()
            
            # Calculate position size recommendation
            position_size = 0
            position_details = {}
            
            if action_name != "NO_ACTION":
                current_price = market_data['close'].iloc[-1]
                position_size, position_details = self.risk_manager.calculate_position_size(
                    symbol, current_price, ai_score=confidence
                )
            
            # Create prediction record
            prediction = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'action': action_name,
                'confidence': confidence,
                'current_price': market_data['close'].iloc[-1],
                'option_data': option_data,
                'position_size': position_size,
                'position_value': position_size * option_data['price'],
                'risk_level': risk_assessment['warnings'][0]['type'] if risk_assessment['warnings'] else 'LOW'
            }
            
            # Store prediction history
            if symbol not in self.prediction_history:
                self.prediction_history[symbol] = []
            
            self.prediction_history[symbol].append(prediction)
            
            # Save to signal directory
            self._save_signal(prediction)
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error getting prediction for {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'action': 'ERROR',
                'error': str(e)
            }
    
    def _save_signal(self, prediction: Dict):
        """Save signal to disk"""
        symbol = prediction['symbol']
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Create directory for symbol
        symbol_dir = self.signals_dir / symbol
        symbol_dir.mkdir(exist_ok=True)
        
        # Create file path
        file_path = symbol_dir / f"{date_str}.json"
        
        # Load existing signals if file exists
        signals = []
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    signals = json.load(f)
            except Exception as e:
                logger.error(f"Error loading signals from {file_path}: {str(e)}")
        
        # Add new signal
        signals.append(prediction)
        
        # Save signals
        with open(file_path, 'w') as f:
            json.dump(signals, f, indent=2)
    
    def execute_virtual_trade(self, prediction: Dict) -> Dict:
        """
        Execute a virtual trade based on a prediction.
        
        Args:
            prediction: Dictionary with prediction results
            
        Returns:
            Dictionary with trade results
        """
        symbol = prediction['symbol']
        action = prediction['action']
        confidence = prediction['confidence']
        
        result = {
            'symbol': symbol,
            'action': action,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'message': ''
        }
        
        # Check if action is valid
        if action not in ['BUY', 'SELL']:
            result['message'] = f"Invalid action: {action}"
            return result
        
        # Get current position
        position = virtual_trader.portfolio.get_position(symbol)
        
        if action == 'BUY':
            # Check if we already have a position
            if position is not None:
                result['message'] = f"Already have a position in {symbol}"
                return result
            
            # Calculate position size
            price = prediction['current_price']
            quantity = prediction.get('position_size', 1)  # Default to 1 if not specified
            
            # Execute buy order
            trade = virtual_trader.buy(
                symbol=symbol,
                price=price,
                quantity=quantity,
                strategy="RL_MODEL",
                confidence=confidence
            )
            
            if trade:
                result['success'] = True
                result['message'] = f"Bought {quantity} shares of {symbol} at ${price:.2f}"
                result['trade'] = trade.to_dict()
                
                # Send notification
                if self.telegram_notifier:
                    self._send_trade_notification(trade, is_entry=True)
            else:
                result['message'] = f"Failed to buy {symbol}"
        
        elif action == 'SELL':
            # Check if we have a position to sell
            if position is None:
                result['message'] = f"No position in {symbol} to sell"
                return result
            
            # Get current price
            price = prediction['current_price']
            
            # Execute sell order
            trade = virtual_trader.sell(
                symbol=symbol,
                price=price
            )
            
            if trade:
                result['success'] = True
                result['message'] = f"Sold {trade.quantity} shares of {symbol} at ${price:.2f}"
                result['trade'] = trade.to_dict()
                
                # Send notification
                if self.telegram_notifier:
                    self._send_trade_notification(trade, is_entry=False)
            else:
                result['message'] = f"Failed to sell {symbol}"
        
        return result
    
    def _send_trade_notification(self, trade, is_entry=True):
        """Send trade notification via Telegram"""
        if not self.telegram_notifier:
            return
        
        if is_entry:
            message = f"ðŸŸ¢ *New Position Opened*\n\n"
            message += f"Symbol: {trade.symbol}\n"
            message += f"Action: {trade.action}\n"
            message += f"Quantity: {trade.quantity}\n"
            message += f"Price: ${trade.entry_price:.2f}\n"
            message += f"Total: ${trade.quantity * trade.entry_price:.2f}\n"
            message += f"Time: {trade.entry_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            if trade.strategy:
                message += f"Strategy: {trade.strategy}\n"
            if trade.confidence:
                message += f"AI Confidence: {trade.confidence:.1%}\n"
        else:
            message = f"ðŸ”´ *Position Closed*\n\n"
            message += f"Symbol: {trade.symbol}\n"
            message += f"Quantity: {trade.quantity}\n"
            message += f"Entry: ${trade.entry_price:.2f}\n"
            message += f"Exit: ${trade.exit_price:.2f}\n"
            message += f"P&L: ${trade.pnl:.2f} ({trade.pnl_pct:.2f}%)\n"
            message += f"Holding Time: {(trade.exit_time - trade.entry_time).total_seconds() / 3600:.1f} hours\n"
        
        self.telegram_notifier.send_message(message)
    
    def auto_update_prices(self):
        """Update prices for all positions in virtual trader"""
        # Get all positions
        positions = virtual_trader.portfolio.get_all_positions()
        
        if not positions:
            return
        
        # Update prices for each position
        updated_prices = {}
        
        for symbol in positions.keys():
            try:
                # Get latest market data
                market_data = self.get_market_data(symbol)
                
                # Get latest price
                current_price = market_data['close'].iloc[-1]
                
                # Add to updated prices
                updated_prices[symbol] = current_price
            except Exception as e:
                logger.error(f"Error updating price for {symbol}: {str(e)}")
        
        # Update portfolio with new prices
        if updated_prices:
            virtual_trader.update_prices(updated_prices)
            logger.info(f"Updated prices for {len(updated_prices)} positions")
    
    def run_predictions(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Run predictions for a list of symbols.
        
        Args:
            symbols: List of symbols to predict
            
        Returns:
            Dictionary of prediction results by symbol
        """
        results = {}
        
        for symbol in symbols:
            try:
                prediction = self.get_prediction(symbol)
                results[symbol] = prediction
                logger.info(f"Prediction for {symbol}: {prediction['action']} (confidence: {prediction['confidence']:.2f})")
            except Exception as e:
                logger.error(f"Error predicting for {symbol}: {str(e)}")
                results[symbol] = {
                    'symbol': symbol,
                    'action': 'ERROR',
                    'error': str(e)
                }
        
        return results
    
    def auto_trade(self, symbols: List[str], min_confidence: float = 0.7) -> Dict[str, Dict]:
        """
        Automatically trade based on predictions for a list of symbols.
        
        Args:
            symbols: List of symbols to trade
            min_confidence: Minimum confidence to execute a trade
            
        Returns:
            Dictionary of trade results by symbol
        """
        results = {}
        
        # Update prices before trading
        self.auto_update_prices()
        
        # Run predictions and trade
        for symbol in symbols:
            try:
                # Get prediction
                prediction = self.get_prediction(symbol)
                
                # Only trade if confidence is high enough
                if prediction['confidence'] >= min_confidence and prediction['action'] != 'NO_ACTION':
                    # Execute trade
                    trade_result = self.execute_virtual_trade(prediction)
                    results[symbol] = trade_result
                    logger.info(f"Traded {symbol}: {trade_result['message']}")
                else:
                    results[symbol] = {
                        'symbol': symbol,
                        'action': 'SKIP',
                        'message': f"Insufficient confidence ({prediction['confidence']:.2f}) or no action"
                    }
                    logger.info(f"Skipped trading {symbol}: {results[symbol]['message']}")
            except Exception as e:
                logger.error(f"Error trading {symbol}: {str(e)}")
                results[symbol] = {
                    'symbol': symbol,
                    'action': 'ERROR',
                    'error': str(e)
                }
        
        return results
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary from virtual trader"""
        return virtual_trader.get_portfolio_summary()
    
    def get_performance_metrics(self) -> Dict:
        """Get performance metrics from virtual trader"""
        return virtual_trader.get_performance_metrics()

# Create singleton instance
trading_integration = TradingIntegration() 