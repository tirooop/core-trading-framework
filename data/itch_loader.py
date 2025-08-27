import pandas as pd
import json
from pathlib import Path
from typing import Dict, Optional, Union
import numpy as np

class ITCHDataLoader:
    """Loader for ITCH Market By Order (MBO) data."""
    
    def __init__(self, data_dir: Union[str, Path] = "data"):
        self.data_dir = Path(data_dir)
        self._load_metadata()
        self._load_symbology()
    
    def _load_metadata(self):
        """Load metadata information."""
        try:
            with open(self.data_dir / "metadata.json", "r") as f:
                self.metadata = json.load(f)
        except FileNotFoundError:
            print("⚠️ Warning: metadata.json not found")
            self.metadata = {}
    
    def _load_symbology(self):
        """Load symbol mapping information."""
        try:
            with open(self.data_dir / "symbology.json", "r") as f:
                self.symbology = json.load(f)
        except FileNotFoundError:
            print("⚠️ Warning: symbology.json not found")
            self.symbology = {}
    
    def load_mbo_data(self, file_name: str = "xnas-itch-20220610.mbo.csv") -> pd.DataFrame:
        """
        Load and process ITCH MBO data.
        
        Args:
            file_name: Name of the MBO data file
            
        Returns:
            Processed DataFrame with OHLCV data
        """
        # Load raw MBO data
        df = pd.read_csv(self.data_dir / file_name)
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ns')
        
        # Set timestamp as index
        df.set_index('timestamp', inplace=True)
        
        # Convert price to dollars
        if 'price' in df.columns:
            df['price'] = df['price'] / 10000  # Convert from 4 decimal places
        
        # Create OHLCV data
        ohlcv = self._create_ohlcv(df)
        
        return ohlcv
    
    def _create_ohlcv(self, df: pd.DataFrame, freq: str = '1min') -> pd.DataFrame:
        """
        Create OHLCV data from MBO data.
        
        Args:
            df: Raw MBO DataFrame
            freq: Resampling frequency
            
        Returns:
            OHLCV DataFrame
        """
        # Resample to desired frequency
        ohlcv = pd.DataFrame()
        
        # Calculate OHLCV
        ohlcv['open'] = df['price'].resample(freq).first()
        ohlcv['high'] = df['price'].resample(freq).max()
        ohlcv['low'] = df['price'].resample(freq).min()
        ohlcv['close'] = df['price'].resample(freq).last()
        ohlcv['volume'] = df['shares'].resample(freq).sum()
        
        # Forward fill missing values
        ohlcv.ffill(inplace=True)
        
        # Calculate additional metrics
        ohlcv['vwap'] = (df['price'] * df['shares']).resample(freq).sum() / df['shares'].resample(freq).sum()
        
        return ohlcv
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """Get symbol mapping information."""
        if self.symbology and 'result' in self.symbology:
            return self.symbology['result'].get(symbol, {})
        return {}
    
    def get_dataset_info(self) -> Dict:
        """Get dataset metadata."""
        if self.metadata and 'query' in self.metadata:
            return {
                'dataset': self.metadata['query'].get('dataset'),
                'start_time': pd.Timestamp(self.metadata['query'].get('start', 0), unit='ns'),
                'end_time': pd.Timestamp(self.metadata['query'].get('end', 0), unit='ns'),
                'symbols': self.metadata['query'].get('symbols', [])
            }
        return {}

# Create a global instance
itch_loader = ITCHDataLoader()

if __name__ == "__main__":
    # Test the loader
    print("Loading ITCH MBO data...")
    df = itch_loader.load_mbo_data()
    print("\nSample OHLCV data:")
    print(df.head())
    
    print("\nDataset info:")
    print(itch_loader.get_dataset_info())
    
    print("\nSymbol info for MSFT:")
    print(itch_loader.get_symbol_info("MSFT")) 