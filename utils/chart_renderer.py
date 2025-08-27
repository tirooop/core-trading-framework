"""
Chart renderer for creating technical analysis charts with multiple indicators.
Supports K-line charts, moving averages, Fisher Transform, MACD, and Bollinger Bands.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import os
from datetime import datetime
from utils.market_data_provider import MarketDataProvider
from utils.technical_indicator_lib import TechnicalIndicatorLib

class ChartRenderer:
    def __init__(self):
        self.data_provider = MarketDataProvider()
        self.indicators = TechnicalIndicatorLib()
        self.output_dir = os.path.join(os.getcwd(), 'temp_charts')
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def render(self, symbol, days=30, include_volume=True):
        """
        Generate a technical analysis chart for the given symbol
        
        Args:
            symbol: Stock ticker symbol
            days: Number of trading days to include
            include_volume: Whether to include volume bars
            
        Returns:
            Path to the generated chart image
        """
        # Fetch market data
        df = self.data_provider.fetch(symbol, days)
        
        # Calculate technical indicators
        df = self.indicators.add_indicators(df)
        
        # Create figure with subplots
        if include_volume:
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), 
                                               gridspec_kw={'height_ratios': [3, 1, 1]})
        else:
            fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(12, 8), 
                                          gridspec_kw={'height_ratios': [3, 1]})
        
        # Format date axis
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        
        # Plot price data
        ax1.plot(df.index, df['close'], label='Close Price', color='black', linewidth=1)
        
        # Plot EMA lines
        ax1.plot(df.index, df['ema20'], label='EMA 20', color='blue', linewidth=1)
        ax1.plot(df.index, df['ema50'], label='EMA 50', color='red', linewidth=1)
        
        # Plot Bollinger Bands
        ax1.plot(df.index, df['upper_band'], 'k--', label='Upper BB', alpha=0.5)
        ax1.plot(df.index, df['lower_band'], 'k--', label='Lower BB', alpha=0.5)
        ax1.fill_between(df.index, df['upper_band'], df['lower_band'], color='gray', alpha=0.1)
        
        # Set title and labels
        current_price = df['close'].iloc[-1]
        change_pct = (df['close'].iloc[-1] / df['close'].iloc[-2] - 1) * 100
        title = f"{symbol}: ${current_price:.2f} ({'+' if change_pct >= 0 else ''}{change_pct:.2f}%)"
        ax1.set_title(title, fontsize=14)
        ax1.set_ylabel('Price ($)', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left')
        
        # Volume subplot
        if include_volume:
            # Plot volume bars
            pos_idx = df['close'] >= df['open']
            neg_idx = df['close'] < df['open']
            
            ax2.bar(df.index[pos_idx], df['volume'][pos_idx], color='green', alpha=0.5, width=0.8)
            ax2.bar(df.index[neg_idx], df['volume'][neg_idx], color='red', alpha=0.5, width=0.8)
            
            # Format volume axis
            ax2.set_ylabel('Volume', fontsize=12)
            ax2.grid(True, alpha=0.3)
            ax2.set_xticklabels([])  # Hide x-axis labels
        
        # MACD subplot
        ax3.plot(df.index, df['macd'], label='MACD', color='blue', linewidth=1)
        ax3.plot(df.index, df['macd_signal'], label='Signal', color='red', linewidth=1)
        ax3.bar(df.index, df['macd_hist'], color=['green' if x >= 0 else 'red' for x in df['macd_hist']], 
                width=0.8, alpha=0.5)
        
        # Fisher Transform as dashed line on the same subplot
        fisher_line = ax3.plot(df.index, df['fisher'], label='Fisher', color='purple', 
                              linestyle='--', linewidth=1)
        
        # Format MACD axis
        ax3.set_ylabel('MACD / Fisher', fontsize=12)
        ax3.grid(True, alpha=0.3)
        ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax3.legend(loc='upper left')
        
        # Adjust layout and save
        plt.tight_layout()
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        save_path = os.path.join(self.output_dir, f"{symbol}_{timestamp}.png")
        plt.savefig(save_path, dpi=150)
        plt.close(fig)
        
        return save_path 