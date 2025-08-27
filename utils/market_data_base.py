"""
市场数据基础模块 - 定义获取市场数据的基类和通用功能
支持多种数据源: yfinance, pandas-datareader, alpaca, polygon
"""
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Optional, Union, Tuple

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("market_data_base")

class MarketDataSource:
    """市场数据获取基类"""
    
    def __init__(self, data_source: str = "yfinance"):
        """
        初始化市场数据源
        
        参数:
            data_source: 数据源选择 ("yfinance", "pandas_datareader", "alpaca", "polygon")
        """
        self.data_source = data_source
        self.is_ready = False
        
        # 尝试初始化选择的数据源
        if data_source == "yfinance":
            self._init_yfinance()
        elif data_source == "pandas_datareader":
            self._init_pandas_datareader()
        elif data_source == "alpaca":
            self._init_alpaca()
        elif data_source == "polygon":
            self._init_polygon()
        else:
            raise ValueError(f"不支持的数据源: {data_source}")
    
    def _init_yfinance(self):
        """初始化yfinance"""
        try:
            import yfinance as yf
            self.yf = yf
            self.is_ready = True
            logger.info("已初始化 yfinance 数据源")
        except ImportError:
            logger.error("未安装yfinance库，请运行: pip install yfinance")
            self.is_ready = False
    
    def _init_pandas_datareader(self):
        """初始化pandas-datareader"""
        try:
            import pandas_datareader as pdr
            self.pdr = pdr
            self.is_ready = True
            logger.info("已初始化 pandas-datareader 数据源")
        except ImportError:
            logger.error("未安装pandas-datareader库，请运行: pip install pandas-datareader")
            self.is_ready = False
    
    def _init_alpaca(self):
        """初始化Alpaca API"""
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            
            # 从环境变量获取API密钥
            api_key = os.environ.get("ALPACA_API_KEY")
            api_secret = os.environ.get("ALPACA_API_SECRET")
            
            if not api_key or not api_secret:
                logger.error("未设置Alpaca API密钥，请设置环境变量ALPACA_API_KEY和ALPACA_API_SECRET")
                self.is_ready = False
                return
                
            self.alpaca_client = StockHistoricalDataClient(api_key, api_secret)
            self.StockBarsRequest = StockBarsRequest
            self.TimeFrame = TimeFrame
            self.is_ready = True
            logger.info("已初始化 Alpaca 数据源")
        except ImportError:
            logger.error("未安装alpaca-py库，请运行: pip install alpaca-py")
            self.is_ready = False
    
    def _init_polygon(self):
        """初始化Polygon.io API"""
        try:
            from polygon import RESTClient
            
            # 从环境变量获取API密钥
            api_key = os.environ.get("POLYGON_API_KEY")
            
            if not api_key:
                logger.error("未设置Polygon API密钥，请设置环境变量POLYGON_API_KEY")
                self.is_ready = False
                return
                
            self.polygon_client = RESTClient(api_key)
            self.is_ready = True
            logger.info("已初始化 Polygon.io 数据源")
        except ImportError:
            logger.error("未安装polygon-api-client库，请运行: pip install polygon-api-client")
            self.is_ready = False
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        获取当前价格
        
        参数:
            symbol: 股票代码
            
        返回:
            当前价格，获取失败返回None
        """
        if not self.is_ready:
            logger.error("数据源未准备好")
            return None
            
        try:
            if self.data_source == "yfinance":
                ticker = self.yf.Ticker(symbol)
                return ticker.info.get('regularMarketPrice')
                
            elif self.data_source == "alpaca":
                # Alpaca获取最新价格需要订阅实时数据，这里使用最近的Bar作为近似
                request_params = self.StockBarsRequest(
                    symbol_or_symbols=[symbol],
                    timeframe=self.TimeFrame.Minute,
                    start=datetime.now() - timedelta(minutes=5)
                )
                bars = self.alpaca_client.get_stock_bars(request_params)
                if not bars.data:
                    return None
                df = bars.df
                return df.iloc[-1]['close']
                
            elif self.data_source == "polygon":
                # 使用Polygon获取最近交易
                resp = self.polygon_client.get_last_trade(ticker=symbol)
                return resp.price
                
            else:
                logger.warning(f"数据源 {self.data_source} 不支持获取实时价格")
                return None
                
        except Exception as e:
            logger.error(f"获取 {symbol} 当前价格失败: {e}")
            return None
    
    def get_historical_data(self, symbol: str, 
                           interval: str = "1d", 
                           period: str = "1mo") -> Optional[pd.DataFrame]:
        """
        获取历史数据
        
        参数:
            symbol: 股票代码
            interval: 时间间隔 ("1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo")
            period: 时间跨度 ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
            
        返回:
            历史数据DataFrame，获取失败返回None
        """
        if not self.is_ready:
            logger.error("数据源未准备好")
            return None
            
        try:
            # 转换period为开始日期
            end_date = datetime.now()
            if period == "1d":
                start_date = end_date - timedelta(days=1)
            elif period == "5d":
                start_date = end_date - timedelta(days=5)
            elif period == "1mo":
                start_date = end_date - timedelta(days=30)
            elif period == "3mo":
                start_date = end_date - timedelta(days=90)
            elif period == "6mo":
                start_date = end_date - timedelta(days=180)
            elif period == "1y":
                start_date = end_date - timedelta(days=365)
            elif period == "2y":
                start_date = end_date - timedelta(days=365*2)
            elif period == "5y":
                start_date = end_date - timedelta(days=365*5)
            else:
                start_date = end_date - timedelta(days=30)  # 默认1个月
            
            if self.data_source == "yfinance":
                ticker = self.yf.Ticker(symbol)
                data = ticker.history(period=period, interval=interval)
                return data
                
            elif self.data_source == "pandas_datareader":
                # pandas-datareader只支持每日数据
                if interval not in ["1d", "daily"]:
                    logger.warning("pandas-datareader只支持每日数据，忽略interval参数")
                
                data = self.pdr.data.get_data_yahoo(symbol, start=start_date, end=end_date)
                return data
                
            elif self.data_source == "alpaca":
                # 转换interval为Alpaca的TimeFrame
                if interval == "1m":
                    timeframe = self.TimeFrame.Minute
                elif interval == "1h":
                    timeframe = self.TimeFrame.Hour
                elif interval == "1d":
                    timeframe = self.TimeFrame.Day
                else:
                    logger.warning(f"Alpaca不支持间隔 {interval}，使用1分钟")
                    timeframe = self.TimeFrame.Minute
                
                request_params = self.StockBarsRequest(
                    symbol_or_symbols=[symbol],
                    timeframe=timeframe,
                    start=start_date,
                    end=end_date
                )
                bars = self.alpaca_client.get_stock_bars(request_params)
                return bars.df
                
            elif self.data_source == "polygon":
                # 转换interval为Polygon的参数
                if interval == "1m":
                    multiplier, timespan = 1, "minute"
                elif interval == "5m":
                    multiplier, timespan = 5, "minute"
                elif interval == "15m":
                    multiplier, timespan = 15, "minute"
                elif interval == "1h":
                    multiplier, timespan = 1, "hour"
                elif interval == "1d":
                    multiplier, timespan = 1, "day"
                else:
                    logger.warning(f"使用默认值替代不支持的间隔 {interval}")
                    multiplier, timespan = 1, "day"
                
                # Polygon API需要日期字符串
                from_date = start_date.strftime('%Y-%m-%d')
                to_date = end_date.strftime('%Y-%m-%d')
                
                # 获取数据
                aggs = self.polygon_client.get_aggs(
                    ticker=symbol,
                    multiplier=multiplier,
                    timespan=timespan,
                    from_=from_date,
                    to=to_date
                )
                
                # 转换为DataFrame
                data = []
                for bar in aggs:
                    data.append({
                        'open': bar.open,
                        'high': bar.high,
                        'low': bar.low,
                        'close': bar.close,
                        'volume': bar.volume,
                        'timestamp': bar.timestamp
                    })
                
                df = pd.DataFrame(data)
                if not df.empty:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                
                return df
        
        except Exception as e:
            logger.error(f"获取 {symbol} 历史数据失败: {e}")
            return None
    
    def get_option_chain(self, symbol: str) -> Optional[Dict]:
        """
        获取期权链数据
        
        参数:
            symbol: 股票代码
            
        返回:
            期权链数据字典，获取失败返回None
        """
        if not self.is_ready:
            logger.error("数据源未准备好")
            return None
            
        try:
            if self.data_source == "yfinance":
                ticker = self.yf.Ticker(symbol)
                return ticker.options
                
            else:
                logger.warning(f"数据源 {self.data_source} 不支持获取期权链")
                return None
                
        except Exception as e:
            logger.error(f"获取 {symbol} 期权链失败: {e}")
            return None
    
    def get_option_data(self, symbol: str, expiration_date: str) -> Optional[Dict]:
        """
        获取特定到期日的期权数据
        
        参数:
            symbol: 股票代码
            expiration_date: 到期日 (YYYY-MM-DD)
            
        返回:
            期权数据字典，包含calls和puts，获取失败返回None
        """
        if not self.is_ready:
            logger.error("数据源未准备好")
            return None
            
        try:
            if self.data_source == "yfinance":
                ticker = self.yf.Ticker(symbol)
                return ticker.option_chain(expiration_date)
                
            else:
                logger.warning(f"数据源 {self.data_source} 不支持获取期权数据")
                return None
                
        except Exception as e:
            logger.error(f"获取 {symbol} 期权数据失败: {e}")
            return None 