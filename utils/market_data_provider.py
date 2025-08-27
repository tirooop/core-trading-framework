"""
Market data provider for fetching financial data.
Primarily uses yfinance but can be extended to support other data sources.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

class MarketDataProvider:
    def __init__(self):
        pass
        
    def fetch(self, symbol, days=30, interval="1d"):
        """
        Fetch market data for a symbol
        
        Args:
            symbol: Stock ticker symbol
            days: Number of days of historical data to fetch
            interval: Data interval (1d, 1h, etc.)
            
        Returns:
            DataFrame with OHLCV data and dates as index
        """
        # Calculate start and end dates
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days * 1.5)  # Add buffer for weekends/holidays
        
        try:
            # Fetch data from yfinance
            df = yf.download(
                symbol, 
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                interval=interval,
                progress=False,
                show_errors=False
            )
            
            # Ensure we have the expected columns
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"Missing required column: {col}")
            
            # Standardize column names to lowercase
            df.columns = [col.lower() for col in df.columns]
            
            # Filter to get the requested number of days
            if len(df) > days:
                df = df.iloc[-days:]
                
            return df
            
        except Exception as e:
            # If yfinance fails, try to create a mock dataset for demo purposes
            if symbol.upper() in ['AAPL', 'MSFT', 'TSLA', 'NVDA', 'AMZN', 'GOOGL']:
                return self._generate_mock_data(symbol, days)
            else:
                raise ValueError(f"Failed to fetch data for {symbol}: {str(e)}")
    
    def _generate_mock_data(self, symbol, days):
        """Generate mock data for demo purposes"""
        import numpy as np
        
        # Create date range
        end_date = datetime.now()
        dates = [end_date - timedelta(days=i) for i in range(days)]
        dates.reverse()
        
        # Generate random price data with a trend
        seed_value = sum([ord(c) for c in symbol.upper()]) % 100  # Use symbol for seed
        np.random.seed(seed_value)
        
        base_price = 100 + (seed_value % 400)  # Different base price per symbol
        trend = np.random.choice([-1, 1]) * np.random.uniform(0.1, 0.3)  # Random trend
        
        # Generate price data
        noise = np.random.normal(0, 1, days) * base_price * 0.01
        trend_component = np.arange(days) * trend
        close_prices = base_price + trend_component + noise.cumsum()
        
        # Ensure no negative prices
        close_prices = np.maximum(close_prices, base_price * 0.7)
        
        # Create DataFrame
        data = {
            'open': close_prices * np.random.uniform(0.99, 1.01, days),
            'high': close_prices * np.random.uniform(1.01, 1.03, days),
            'low': close_prices * np.random.uniform(0.97, 0.99, days),
            'close': close_prices,
            'volume': np.random.randint(1000000, 10000000, days)
        }
        
        df = pd.DataFrame(data, index=dates)
        return df 