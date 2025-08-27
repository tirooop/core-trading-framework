"""
Yahoo Finance 数据源实现
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import Dict, Optional
from .base_data_source import BaseDataSource

class YahooDataSource(BaseDataSource):
    """Yahoo Finance 数据源"""
    
    def get_stock_data(self, 
                       symbol: str, 
                       start_date: str, 
                       end_date: str, 
                       interval: str = "1d") -> pd.DataFrame:
        """获取股票历史数据"""
        df = yf.download(symbol, start=start_date, end=end_date, interval=interval)
        df = df.rename(columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume"
        })
        return df

    def get_option_chain(self, 
                        symbol: str, 
                        expiry: Optional[str] = None) -> Dict:
        """获取期权链数据"""
        ticker = yf.Ticker(symbol)
        
        # 如果没有指定到期日，使用最近的到期日
        if expiry is None:
            expiry = ticker.options[0]
            
        # 获取期权链
        opt = ticker.option_chain(expiry)
        
        # 处理列名
        calls = opt.calls.rename(columns={
            'lastPrice': 'last',
            'bid': 'bid',
            'ask': 'ask',
            'change': 'change',
            'percentChange': 'change_percent',
            'volume': 'volume',
            'openInterest': 'open_interest',
            'impliedVolatility': 'implied_volatility'
        })
        
        puts = opt.puts.rename(columns={
            'lastPrice': 'last',
            'bid': 'bid',
            'ask': 'ask',
            'change': 'change',
            'percentChange': 'change_percent',
            'volume': 'volume',
            'openInterest': 'open_interest',
            'impliedVolatility': 'implied_volatility'
        })
        
        return {
            "calls": calls,
            "puts": puts,
            "expiry": expiry
        }
        
    def get_realtime_quote(self, symbol: str) -> Dict:
        """获取实时报价"""
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        return {
            "last": info.get("regularMarketPrice", None),
            "change": info.get("regularMarketChange", None),
            "change_percent": info.get("regularMarketChangePercent", None),
            "volume": info.get("regularMarketVolume", None),
            "bid": info.get("bid", None),
            "ask": info.get("ask", None),
            "timestamp": datetime.now().isoformat()
        } 