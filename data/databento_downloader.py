import os
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
import pandas as pd
from databento import DBNStore, Dataset
import yaml
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class DatabentoDownloader:
    """
    A class to download market data from Databento that can be used as a drop-in replacement for yfinance.
    """
    
    def __init__(self):
        self.api_key = os.getenv('DATABENTO_API_KEY')
        if not self.api_key:
            raise ValueError("DATABENTO_API_KEY not found in environment variables")
        
        self.client = DBNStore(key=self.api_key)
        self.cache = {}  # Simple in-memory cache
    
    def download(
        self,
        tickers: Union[str, List[str]],
        start: Optional[str] = None,
        end: Optional[str] = None,
        period: Optional[str] = None,
        interval: str = "1d",
        group_by: str = "ticker",
        progress: bool = True,
        **kwargs
    ) -> pd.DataFrame:
        """
        Download market data from Databento. Interface similar to yfinance.download().
        
        Parameters:
        -----------
        tickers : str or list
            Single ticker or list of tickers
        start : str, optional
            Download start date
        end : str, optional
            Download end date
        period : str, optional
            Download period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval : str, optional
            Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        group_by : str, optional
            Group by 'ticker' or 'column'
        progress : bool, optional
            Display progress bar
            
        Returns:
        --------
        pd.DataFrame
            Downloaded data in pandas DataFrame format
        """
        # Convert tickers to list if it's a string
        if isinstance(tickers, str):
            tickers = [tickers]
        
        # Handle period parameter to determine start and end dates
        if period and not (start and end):
            end = datetime.now()
            if period == "1d":
                start = end - timedelta(days=1)
            elif period == "5d":
                start = end - timedelta(days=5)
            elif period == "1mo":
                start = end - timedelta(days=30)
            elif period == "3mo":
                start = end - timedelta(days=90)
            elif period == "6mo":
                start = end - timedelta(days=180)
            elif period == "1y":
                start = end - timedelta(days=365)
            elif period == "2y":
                start = end - timedelta(days=730)
            elif period == "5y":
                start = end - timedelta(days=1825)
            elif period == "10y":
                start = end - timedelta(days=3650)
            elif period == "ytd":
                start = datetime(end.year, 1, 1)
            else:  # default to 1 month
                start = end - timedelta(days=30)
            
            start = start.strftime("%Y-%m-%d")
            end = end.strftime("%Y-%m-%d")
        
        # Convert interval to Databento format
        databento_interval = self._convert_interval(interval)
        
        # Check cache first
        cache_key = f"{','.join(tickers)}_{start}_{end}_{interval}"
        if cache_key in self.cache:
            logger.info(f"Using cached data for {tickers}")
            return self.cache[cache_key]
        
        logger.info(f"Downloading data for {tickers} from {start} to {end}")
        
        # Create empty DataFrame to store results
        result_df = pd.DataFrame()
        
        try:
            # Process each ticker
            for ticker in tickers:
                df = self._download_single_ticker(ticker, start, end, databento_interval)
                
                if df is not None and not df.empty:
                    if group_by == "ticker":
                        # Add ticker as a column if grouping by ticker
                        df['Ticker'] = ticker
                        result_df = pd.concat([result_df, df])
                    else:
                        # For column-wise, store each ticker as a separate column level
                        df_columns = pd.MultiIndex.from_product([[ticker], df.columns])
                        df.columns = df_columns
                        if result_df.empty:
                            result_df = df
                        else:
                            result_df = pd.concat([result_df, df], axis=1)
            
            # Cache the result
            self.cache[cache_key] = result_df
            
            return result_df
            
        except Exception as e:
            logger.error(f"Error downloading data: {str(e)}")
            return pd.DataFrame()  # Return empty DataFrame on error
    
    def _download_single_ticker(self, ticker: str, start: str, end: str, interval: str) -> pd.DataFrame:
        """Download data for a single ticker."""
        try:
            # For equity data
            df = self.client.timeseries.get_range(
                dataset=Dataset.GLBX_MDP3,  # Use appropriate dataset for your subscription
                symbols=[ticker],
                schema="ohlcv",
                start=start,
                end=end,
                time_format="nanos",
                session_filter="RTH"  # Regular Trading Hours
            )
            
            # Rename columns to match yfinance format
            if not df.empty:
                df = df.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                })
                
                # Set ts_event as index and convert to datetime
                if 'ts_event' in df.columns:
                    df['Date'] = pd.to_datetime(df['ts_event'], unit='ns')
                    df = df.set_index('Date')
                
                # Drop unnecessary columns
                columns_to_keep = ['Open', 'High', 'Low', 'Close', 'Volume']
                df = df[columns_to_keep]
                
                # Resample data to the requested interval
                df = self._resample_data(df, interval)
            
            return df
            
        except Exception as e:
            logger.error(f"Error downloading data for {ticker}: {str(e)}")
            return pd.DataFrame()
    
    def _convert_interval(self, yf_interval: str) -> str:
        """Convert yfinance interval format to Databento format."""
        interval_map = {
            '1m': '1min',
            '2m': '2min',
            '5m': '5min',
            '15m': '15min',
            '30m': '30min',
            '60m': '1h',
            '90m': '90min',
            '1h': '1h',
            '1d': '1d',
            '5d': '5d',
            '1wk': '1w',
            '1mo': '1mo',
            '3mo': '3mo'
        }
        return interval_map.get(yf_interval, '1d')
    
    def _resample_data(self, df: pd.DataFrame, interval: str) -> pd.DataFrame:
        """Resample data to the requested interval."""
        if df.empty:
            return df
            
        # Define how to resample
        if interval.endswith('min'):
            minutes = int(interval.replace('min', ''))
            rule = f'{minutes}T'
        elif interval.endswith('h'):
            hours = int(interval.replace('h', ''))
            rule = f'{hours}H'
        elif interval == '1d':
            rule = 'D'
        elif interval == '1w':
            rule = 'W'
        elif interval == '1mo':
            rule = 'M'
        else:
            rule = 'D'  # Default to daily
        
        # Apply resampling
        resampled = df.resample(rule).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        })
        
        return resampled.dropna()
    
    # Method to match yfinance Ticker objects
    def Ticker(self, ticker: str):
        """Create a Ticker instance similar to yfinance.Ticker."""
        return DatabentoTicker(ticker, self)


class DatabentoTicker:
    """A class to mimic yfinance.Ticker functionality."""
    
    def __init__(self, ticker: str, downloader: DatabentoDownloader):
        self.ticker = ticker
        self.downloader = downloader
        self._info = None
        self._history = None
    
    def history(
        self,
        period: str = "1mo",
        interval: str = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
        **kwargs
    ) -> pd.DataFrame:
        """Get historical market data."""
        df = self.downloader.download(
            tickers=self.ticker,
            period=period,
            interval=interval,
            start=start,
            end=end,
            **kwargs
        )
        
        # If data is grouped by ticker, filter for just this ticker
        if 'Ticker' in df.columns:
            df = df[df['Ticker'] == self.ticker].drop(columns=['Ticker'])
            
        self._history = df
        return df
    
    @property
    def info(self) -> Dict[str, Any]:
        """Get information about the ticker."""
        if self._info is None:
            # In a real implementation, this would fetch actual data
            self._info = {
                'symbol': self.ticker,
                'shortName': self.ticker,
                'longName': f"{self.ticker} via Databento",
                'sector': "Unknown",
                'industry': "Unknown",
                'marketCap': None,
                'previousClose': None
            }
        return self._info


# Create a function similar to yfinance.download for easy drop-in replacement
def download(*args, **kwargs) -> pd.DataFrame:
    """Drop-in replacement for yfinance.download function."""
    downloader = DatabentoDownloader()
    return downloader.download(*args, **kwargs)

# Use this similar to: import yfinance as yf
# from data.databento_downloader import download as yf_download
# df = yf_download("AAPL", period="1mo") 