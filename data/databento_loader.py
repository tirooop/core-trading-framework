import os
from typing import Optional, List
from datetime import datetime
import pandas as pd
from databento import DBNStore, Dataset
import yaml
from dotenv import load_dotenv

load_dotenv()

class DatabentoLoader:
    def __init__(self, config_path: str = "../config/config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)['data']
        
        self.api_key = os.getenv('DATABENTO_API_KEY')
        if not self.api_key:
            raise ValueError("DATABENTO_API_KEY not found in environment variables")
        
        self.client = DBNStore(key=self.api_key)
        
    def download_option_data(
        self,
        symbol: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        save: bool = True
    ) -> pd.DataFrame:
        """Download option data from Databento."""
        symbol = symbol or self.config['symbol']
        start = start or self.config['start_date']
        end = end or self.config['end_date']
        
        print(f"Downloading {symbol} options data from {start} to {end}")
        
        df = self.client.timeseries.get_range(
            dataset=Dataset.OPTIONS,
            symbols=[symbol],
            schema="ohlcv-1s",
            start=start,
            end=end,
        )
        
        if save:
            os.makedirs(self.config['data_dir'], exist_ok=True)
            output_path = os.path.join(
                self.config['data_dir'],
                f"{symbol}_options_{start}_{end}.csv"
            )
            df.to_csv(output_path, index=False)
            print(f"Data saved to {output_path}")
        
        return df
    
    def load_local_data(self, file_path: str) -> pd.DataFrame:
        """Load previously downloaded data from local file."""
        return pd.read_csv(file_path)

if __name__ == "__main__":
    loader = DatabentoLoader()
    data = loader.download_option_data() 