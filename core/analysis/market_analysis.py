#!/usr/bin/env python
# Market Data Analysis and Signal Generation

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

# Import custom modules
try:
    # Try to import the standalone Google Finance module
    from standalone_google_finance import get_historical_data, get_options_chain
except ImportError:
    print("Warning: Could not import standalone_google_finance module")


def setup_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Market Data Analysis')
    parser.add_argument('--symbol', type=str, default='SPY', help='Stock symbol to analyze')
    parser.add_argument('--days', type=int, default=30, help='Number of days of data to analyze')
    parser.add_argument('--generate-signals', action='store_true', help='Generate trading signals')
    parser.add_argument('--use-options', action='store_true', help='Include options data in analysis')
    parser.add_argument('--plot', action='store_true', help='Generate charts')
    parser.add_argument('--output', type=str, default='data/signals', help='Output directory for signals')
    parser.add_argument('--threshold', type=float, default=0.75, help='Signal confidence threshold (0-1)')
    
    return parser.parse_args()


def load_historical_data(symbol, days=30):
    """Load historical price data from files or API"""
    
    # Try to load from recent data files first
    data_dir = "data/historical"
    today = datetime.now().strftime('%Y%m%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    
    # Look for recent data files
    for date_str in [today, yesterday]:
        filename = f"{data_dir}/{symbol}_daily_{date_str}.csv"
        if os.path.exists(filename):
            try:
                df = pd.read_csv(filename)
                print(f"Loaded historical data from {filename}")
                return df
            except Exception as e:
                print(f"Error loading {filename}: {e}")
    
    # If we couldn't load from files, try to get from API
    try:
        print(f"Fetching {symbol} data from Google Finance API...")
        df = get_historical_data(symbol, '1d', days)
        return df
    except Exception as e:
        print(f"Google Finance API error: {e}")
        
        # Try Yahoo Finance as fallback
        try:
            import yfinance as yf
            print(f"Trying Yahoo Finance as fallback...")
            data = yf.download(symbol, period=f"{days}d")
            return data
        except Exception as ye:
            print(f"Yahoo Finance fallback failed: {ye}")
            return None


def calculate_technical_indicators(df):
    """Calculate technical indicators from price data"""
    
    # Create a copy of dataframe to avoid warnings
    df = df.copy()
    
    # Moving Averages
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    
    # MACD
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal']
    
    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + 2 * df['BB_Std']
    df['BB_Lower'] = df['BB_Middle'] - 2 * df['BB_Std']
    
    # Volatility
    df['Volatility'] = df['Close'].rolling(window=20).std() / df['Close'].rolling(window=20).mean() * 100
    
    # Drop NaN values from indicator calculations
    df = df.dropna()
    
    return df


def generate_signals(df, symbol, threshold=0.75):
    """Generate trading signals based on technical analysis"""
    
    signals = []
    
    if df is None or len(df) < 50:
        print(f"Error: Not enough data for {symbol} to generate signals")
        return signals
    
    # Get the latest data
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Initialize signal score (0-1 scale)
    buy_score = 0.0
    sell_score = 0.0
    factors = 0
    
    # 1. Moving Average Crossover
    if prev['MA5'] <= prev['MA20'] and latest['MA5'] > latest['MA20']:
        buy_score += 1.0
        factors += 1
    elif prev['MA5'] >= prev['MA20'] and latest['MA5'] < latest['MA20']:
        sell_score += 1.0
        factors += 1
    
    # 2. MACD Crossover
    if prev['MACD'] <= prev['Signal'] and latest['MACD'] > latest['Signal']:
        buy_score += 1.0
        factors += 1
    elif prev['MACD'] >= prev['Signal'] and latest['MACD'] < latest['Signal']:
        sell_score += 1.0
        factors += 1
    
    # 3. RSI Overbought/Oversold
    if latest['RSI'] < 30:
        buy_score += 1.0
        factors += 1
    elif latest['RSI'] > 70:
        sell_score += 1.0
        factors += 1
    
    # 4. Bollinger Band Breakout
    if latest['Close'] < latest['BB_Lower']:
        buy_score += 0.5
        factors += 0.5
    elif latest['Close'] > latest['BB_Upper']:
        sell_score += 0.5
        factors += 0.5
    
    # 5. Price Trend
    price_change = (latest['Close'] - df['Close'].iloc[-5]) / df['Close'].iloc[-5]
    if price_change > 0.02:  # 2% up trend
        buy_score += 0.5
        factors += 0.5
    elif price_change < -0.02:  # 2% down trend
        sell_score += 0.5
        factors += 0.5
    
    # Calculate final scores
    if factors > 0:
        buy_score = buy_score / factors
        sell_score = sell_score / factors
    
    # Generate signals if scores exceed threshold
    if buy_score > threshold:
        signal = {
            "symbol": symbol,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "price": latest['Close'],
            "action": "BUY",
            "confidence": round(buy_score * 100),
            "reason": "Technical analysis signals bullish trend",
            "indicators": {
                "MA_crossover": prev['MA5'] <= prev['MA20'] and latest['MA5'] > latest['MA20'],
                "MACD_crossover": prev['MACD'] <= prev['Signal'] and latest['MACD'] > latest['Signal'],
                "RSI": round(latest['RSI'], 2),
                "BB_position": (latest['Close'] - latest['BB_Lower']) / (latest['BB_Upper'] - latest['BB_Lower'])
            }
        }
        signals.append(signal)
        
    elif sell_score > threshold:
        signal = {
            "symbol": symbol,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "price": latest['Close'],
            "action": "SELL",
            "confidence": round(sell_score * 100),
            "reason": "Technical analysis signals bearish trend",
            "indicators": {
                "MA_crossover": prev['MA5'] >= prev['MA20'] and latest['MA5'] < latest['MA20'],
                "MACD_crossover": prev['MACD'] >= prev['Signal'] and latest['MACD'] < latest['Signal'],
                "RSI": round(latest['RSI'], 2),
                "BB_position": (latest['Close'] - latest['BB_Lower']) / (latest['BB_Upper'] - latest['BB_Lower'])
            }
        }
        signals.append(signal)
    
    return signals


def generate_option_signals(symbol, threshold=0.75):
    """Generate option trading signals based on volatility and pricing"""
    
    signals = []
    
    try:
        # Get options chain
        options_data = get_options_chain(symbol)
        if not options_data:
            return signals
        
        # Get historical data for volatility comparison
        hist_data = load_historical_data(symbol, days=30)
        if hist_data is None:
            return signals
        
        # Calculate historical volatility
        hist_vol = hist_data['Close'].pct_change().std() * np.sqrt(252) * 100
        
        # Get current price
        current_price = hist_data['Close'].iloc[-1]
        
        # Find interesting options
        for expiry in options_data:
            days_to_expiry = (datetime.strptime(expiry, '%Y-%m-%d') - datetime.now()).days
            
            # Skip if less than 7 days or more than 45 days to expiry
            if days_to_expiry < 7 or days_to_expiry > 45:
                continue
            
            calls = options_data[expiry]['calls']
            puts = options_data[expiry]['puts']
            
            # Analyze calls
            for call in calls:
                if abs(call['strike'] - current_price) / current_price < 0.05:  # Near the money
                    if call['impliedVolatility'] > hist_vol * 1.2:  # Implied vol > historical vol
                        signal = {
                            "symbol": f"{symbol} {expiry} C{call['strike']}",
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "price": call['lastPrice'],
                            "action": "SELL_TO_OPEN",  # Sell overpriced options
                            "confidence": round(min(0.95, (call['impliedVolatility'] / hist_vol) * 0.7) * 100),
                            "reason": "Implied volatility significantly higher than historical",
                            "indicators": {
                                "implied_vol": round(call['impliedVolatility'], 2),
                                "hist_vol": round(hist_vol, 2),
                                "vol_ratio": round(call['impliedVolatility'] / hist_vol, 2),
                                "days_to_expiry": days_to_expiry
                            }
                        }
                        signals.append(signal)
            
            # Analyze puts
            for put in puts:
                if abs(put['strike'] - current_price) / current_price < 0.05:  # Near the money
                    if put['impliedVolatility'] < hist_vol * 0.8:  # Implied vol < historical vol
                        signal = {
                            "symbol": f"{symbol} {expiry} P{put['strike']}",
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "price": put['lastPrice'],
                            "action": "BUY_TO_OPEN",  # Buy underpriced options
                            "confidence": round(min(0.95, (hist_vol / put['impliedVolatility']) * 0.7) * 100),
                            "reason": "Implied volatility significantly lower than historical",
                            "indicators": {
                                "implied_vol": round(put['impliedVolatility'], 2),
                                "hist_vol": round(hist_vol, 2),
                                "vol_ratio": round(put['impliedVolatility'] / hist_vol, 2),
                                "days_to_expiry": days_to_expiry
                            }
                        }
                        signals.append(signal)
    
    except Exception as e:
        print(f"Error generating option signals: {e}")
    
    return signals


def plot_analysis(df, symbol):
    """Generate plots for technical analysis"""
    
    try:
        # Create a figure with subplots
        fig, axs = plt.subplots(3, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [2, 1, 1]})
        
        # Plot 1: Price with MA and Bollinger Bands
        axs[0].plot(df.index, df['Close'], label='Price', color='blue')
        axs[0].plot(df.index, df['MA20'], label='MA20', color='orange')
        axs[0].plot(df.index, df['MA50'], label='MA50', color='green')
        axs[0].plot(df.index, df['BB_Upper'], label='BB Upper', color='red', linestyle='--')
        axs[0].plot(df.index, df['BB_Lower'], label='BB Lower', color='red', linestyle='--')
        axs[0].fill_between(df.index, df['BB_Upper'], df['BB_Lower'], color='gray', alpha=0.2)
        axs[0].set_title(f'{symbol} Technical Analysis')
        axs[0].set_ylabel('Price')
        axs[0].legend()
        axs[0].grid(True)
        
        # Plot 2: MACD
        axs[1].plot(df.index, df['MACD'], label='MACD', color='blue')
        axs[1].plot(df.index, df['Signal'], label='Signal', color='red')
        axs[1].bar(df.index, df['MACD_Hist'], label='Histogram', color='green', alpha=0.5)
        axs[1].set_ylabel('MACD')
        axs[1].legend()
        axs[1].grid(True)
        
        # Plot 3: RSI
        axs[2].plot(df.index, df['RSI'], label='RSI', color='purple')
        axs[2].axhline(y=70, color='red', linestyle='--')
        axs[2].axhline(y=30, color='green', linestyle='--')
        axs[2].set_ylabel('RSI')
        axs[2].set_ylim(0, 100)
        axs[2].legend()
        axs[2].grid(True)
        
        plt.tight_layout()
        
        # Save the plot to a file
        timestamp = datetime.now().strftime('%Y%m%d')
        output_dir = 'data/analysis'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        plt.savefig(f'{output_dir}/{symbol}_analysis_{timestamp}.png')
        
        print(f"Technical analysis plot saved to {output_dir}/{symbol}_analysis_{timestamp}.png")
        
    except Exception as e:
        print(f"Error creating plot: {e}")


def main():
    """Main function"""
    args = setup_args()
    
    # Ensure the output directory exists
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    
    # Load and analyze price data
    df = load_historical_data(args.symbol, args.days)
    
    if df is None:
        print(f"Error: Could not load data for {args.symbol}")
        sys.exit(1)
    
    # Calculate technical indicators
    df = calculate_technical_indicators(df)
    
    # Generate and output signals if requested
    if args.generate_signals:
        # Generate signals from price data
        signals = generate_signals(df, args.symbol, args.threshold)
        
        # Generate option signals if requested
        if args.use_options:
            option_signals = generate_option_signals(args.symbol, args.threshold)
            signals.extend(option_signals)
        
        # Output signals
        if signals:
            for signal in signals:
                # Output signal in a format that can be captured by PowerShell
                print(f"SIGNAL: {json.dumps(signal)}")
            
            # Save signals to file
            try:
                timestamp = datetime.now().strftime('%Y%m%d')
                signal_file = f"{args.output}/{args.symbol}_signals_{timestamp}.json"
                with open(signal_file, 'w') as f:
                    json.dump(signals, f, indent=2)
                print(f"Signals saved to {signal_file}")
            except Exception as e:
                print(f"Error saving signals to file: {e}")
        else:
            print(f"No trading signals generated for {args.symbol}")
    
    # Generate plots if requested
    if args.plot:
        plot_analysis(df, args.symbol)


if __name__ == "__main__":
    main() 