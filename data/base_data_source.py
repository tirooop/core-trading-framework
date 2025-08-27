"""
基础数据源接口定义
"""

from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime
from typing import Dict, Optional

class BaseDataSource(ABC):
    """数据源基类"""
    
    @abstractmethod
    def get_stock_data(self, 
                       symbol: str, 
                       start_date: str, 
                       end_date: str, 
                       interval: str = "1d") -> pd.DataFrame:
        """
        获取股票历史数据
        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            interval: 时间间隔 ("1m", "5m", "1h", "1d", "1wk", "1mo")
        Returns:
            DataFrame with columns: open, high, low, close, adj_close, volume
        """
        pass

    @abstractmethod
    def get_option_chain(self, 
                        symbol: str, 
                        expiry: Optional[str] = None) -> Dict:
        """
        获取期权链数据
        Args:
            symbol: 股票代码
            expiry: 到期日 (YYYY-MM-DD)，如果不指定则返回最近到期日
        Returns:
            Dict containing:
            - calls: DataFrame of call options
            - puts: DataFrame of put options
            - expiry: expiration date
        """
        pass
        
    @abstractmethod
    def get_realtime_quote(self, symbol: str) -> Dict:
        """
        获取实时报价
        Args:
            symbol: 股票代码
        Returns:
            Dict containing current price, bid, ask, etc.
        """
        pass 