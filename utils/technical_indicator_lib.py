"""
Technical indicator library for calculating common technical analysis indicators.
Includes moving averages, MACD, Fisher Transform, and Bollinger Bands.
"""

import pandas as pd
import numpy as np

class TechnicalIndicatorLib:
    def add_indicators(self, df):
        """
        Add technical indicators to a DataFrame
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added indicator columns
        """
        # Copy to avoid modifying original
        df = df.copy()
        
        # Simple moving averages
        df['sma20'] = df['close'].rolling(window=20).mean()
        df['sma50'] = df['close'].rolling(window=50).mean()
        
        # Exponential moving averages
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # Bollinger Bands
        df['middle_band'] = df['close'].rolling(window=20).mean()
        std_dev = df['close'].rolling(window=20).std()
        df['upper_band'] = df['middle_band'] + (std_dev * 2)
        df['lower_band'] = df['middle_band'] - (std_dev * 2)
        
        # MACD (Moving Average Convergence Divergence)
        df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema12'] - df['ema26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Fisher Transform
        self._add_fisher_transform(df)
        
        # RSI (Relative Strength Index)
        self._add_rsi(df)
        
        return df
    
    def _add_fisher_transform(self, df, period=10):
        """
        Add Fisher Transform indicator
        
        The Fisher Transform creates a nearly Gaussian probability density function 
        by normalizing prices and applying an inverse hyperbolic sine function.
        """
        # Get min and max of price
        df['fisher_high'] = df['close'].rolling(window=period).max()
        df['fisher_low'] = df['close'].rolling(window=period).min()
        
        # Normalize price between -1 and 1
        df['fisher_norm'] = (2 * ((df['close'] - df['fisher_low']) / 
                              (df['fisher_high'] - df['fisher_low'])) - 1)
        
        # Apply boundary constraints
        df['fisher_norm'] = df['fisher_norm'].clip(-0.999, 0.999)
        
        # Apply Fisher Transform
        df['fisher'] = 0.5 * np.log((1 + df['fisher_norm']) / (1 - df['fisher_norm']))
        
        # Clean up temporary columns
        df.drop(['fisher_high', 'fisher_low', 'fisher_norm'], axis=1, inplace=True)
        
        return df
    
    def _add_rsi(self, df, period=14):
        """Add Relative Strength Index"""
        # Calculate price changes
        delta = df['close'].diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and loss
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df
    
    def get_trend_strength(self, df):
        """
        Calculate trend strength based on ADX (Average Directional Index)
        
        Returns:
            Float between 0-100 indicating trend strength
        """
        # Use Fisher transform direction and magnitude as simplified trend strength
        if 'fisher' not in df.columns:
            self._add_fisher_transform(df)
            
        latest_fisher = df['fisher'].iloc[-1]
        # Normalize between 0-100
        trend_strength = min(100, abs(latest_fisher) * 33)
        
        return trend_strength
    
    def get_trend_direction(self, df):
        """
        Determine trend direction (bullish, bearish, neutral)
        
        Returns:
            String indicating trend direction
        """
        # Simple trend direction based on fisher and EMA relationship
        if 'fisher' not in df.columns or 'ema20' not in df.columns:
            df = self.add_indicators(df)
            
        # Get latest values
        fisher = df['fisher'].iloc[-1]
        price = df['close'].iloc[-1]
        ema20 = df['ema20'].iloc[-1]
        
        # Determine trend
        if fisher > 0.5 and price > ema20:
            return "bullish"
        elif fisher < -0.5 and price < ema20:
            return "bearish"
        else:
            return "neutral" 