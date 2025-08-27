import os
from typing import Optional, Union
from datetime import datetime, date
import pandas as pd
from databento import Historical
from dotenv import load_dotenv
from pathlib import Path

class DatabentoDownloader:
    """Handles data downloading and caching from Databento."""
    
    def __init__(self, cache_dir: str = "data/cache"):
        load_dotenv()
        self.api_key = os.getenv("DATABENTO_API_KEY")
        if not self.api_key:
            raise ValueError("DATABENTO_API_KEY not found in environment variables")
        
        self.client = Historical(api_key=self.api_key)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, symbol: str, start: str, end: str, schema: str) -> Path:
        """Generate a cache file path based on parameters."""
        return self.cache_dir / f"{symbol}_{start}_{end}_{schema}.parquet"
    
    def fetch_data(self,
                   symbol: str,
                   start: Union[str, date, datetime],
                   end: Union[str, date, datetime],
                   schema: str = "trades",
                   force_download: bool = False) -> pd.DataFrame:
        """
        Fetch market data from Databento with caching support.
        
        Args:
            symbol: Trading symbol (e.g., "ESH4", "QQQ")
            start: Start date/time
            end: End date/time
            schema: Data schema ("trades", "mbo", "book", "ohlcv-1s", etc.)
            force_download: If True, ignore cache and force new download
            
        Returns:
            pandas.DataFrame with the requested market data
        """
        # Convert dates to string format if needed
        start_str = start.strftime("%Y-%m-%d") if isinstance(start, (date, datetime)) else start
        end_str = end.strftime("%Y-%m-%d") if isinstance(end, (date, datetime)) else end
        
        cache_path = self._get_cache_path(symbol, start_str, end_str, schema)
        
        # Check cache first
        if not force_download and cache_path.exists():
            print(f"Loading cached data from {cache_path}")
            return pd.read_parquet(cache_path)
        
        # Download fresh data
        print(f"Downloading data for {symbol} from {start_str} to {end_str}")
        try:
            data = self.client.timeseries.get_range(
                dataset="GLBX.MDP3",  # Can be parameterized based on symbol
                symbols=symbol,
                start=f"{start_str}T00:00:00Z",
                end=f"{end_str}T23:59:59Z",
                schema=schema,
                encoding="dbn",
                stype_in="raw_symbol",
                stype_out="product_id"
            )
            
            df = data.to_df()
            
            # Cache the data
            df.to_parquet(cache_path)
            print(f"Data cached to {cache_path}")
            
            return df
            
        except Exception as e:
            print(f"Error downloading data: {e}")
            raise
    
    def list_available_datasets(self) -> list:
        """List all available datasets from Databento."""
        return self.client.metadata.list_datasets()
    
    def clear_cache(self, symbol: Optional[str] = None):
        """
        Clear cached data files.
        
        Args:
            symbol: If provided, only clear cache for this symbol
        """
        if symbol:
            pattern = f"{symbol}_*.parquet"
            files = self.cache_dir.glob(pattern)
        else:
            files = self.cache_dir.glob("*.parquet")
            
        for file in files:
            file.unlink()
            print(f"Deleted cache file: {file}")

# Create a global instance
downloader = DatabentoDownloader()

if __name__ == "__main__":
    # Test the downloader
    print("Available datasets:", downloader.list_available_datasets())
    
    # Test data download
    df = downloader.fetch_data(
        symbol="ESH4",
        start="2024-04-01",
        end="2024-04-01",
        schema="trades"
    )
    print("\nSample data:")
    print(df.head()) 