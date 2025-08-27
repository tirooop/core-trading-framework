import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from polygon import RESTClient
from polygon.rest.models import Agg

class PolygonDataSource:
    """
    Polygon.io data source for real-time market data
    """
    def __init__(self, api_key: str):
        self.client = RESTClient(api_key)
        
    def get_minute_bars(self, 
                       symbol: str, 
                       timespan: str = "minute",
                       multiplier: int = 1,
                       from_date: Optional[datetime] = None,
                       to_date: Optional[datetime] = None,
                       limit: int = 100) -> pd.DataFrame:
        """
        Get minute bars for a symbol
        
        Args:
            symbol: Stock symbol
            timespan: Time span (minute, hour, day, etc.)
            multiplier: Time multiplier (e.g. 1 for 1 minute, 3 for 3 minutes)
            from_date: Start date
            to_date: End date
            limit: Number of bars to return
            
        Returns:
            DataFrame with OHLCV data
        """
        if not to_date:
            to_date = datetime.now()
        if not from_date:
            from_date = to_date - timedelta(days=1)
            
        bars = self.client.get_aggs(
            symbol,
            multiplier,
            timespan,
            from_date,
            to_date,
            limit=limit
        )
        
        if not bars:
            return pd.DataFrame()
            
        df = pd.DataFrame([{
            'timestamp': b.timestamp,
            'open': b.open,
            'high': b.high,
            'low': b.low,
            'close': b.close,
            'volume': b.volume,
            'vwap': b.vwap,
            'transactions': b.transactions
        } for b in bars])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
        
    def get_option_chain(self, 
                        underlying_symbol: str,
                        expiration_date: Optional[datetime] = None) -> Dict:
        """
        Get option chain data for a symbol
        
        Args:
            underlying_symbol: Underlying stock symbol
            expiration_date: Option expiration date
            
        Returns:
            Dictionary containing calls and puts data
        """
        options = self.client.get_options_chain(
            underlying_symbol,
            expiration_date=expiration_date.strftime('%Y-%m-%d') if expiration_date else None
        )
        return options
        
    def get_last_trade(self, symbol: str) -> Dict:
        """
        Get last trade for a symbol
        
        Args:
            symbol: Stock or option symbol
            
        Returns:
            Dictionary containing last trade information
        """
        trade = self.client.get_last_trade(symbol)
        return {
            'price': trade.price,
            'size': trade.size,
            'timestamp': pd.to_datetime(trade.sip_timestamp, unit='ns')
        } 