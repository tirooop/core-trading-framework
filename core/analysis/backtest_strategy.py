#!/usr/bin/env python
# Strategy Backtesting Module for Trading System

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
    from analyze_market_data import calculate_technical_indicators, generate_signals
except ImportError:
    print("Warning: Could not import analyze_market_data module")


def setup_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Strategy Backtesting')
    parser.add_argument('--symbols', type=str, nargs='+', default=['SPY', 'QQQ', 'AAPL', 'MSFT', 'TSLA', 'NVDA'], 
                       help='Stock symbols to backtest')
    parser.add_argument('--days', type=int, default=90, help='Number of days for backtest')
    parser.add_argument('--initial-capital', type=float, default=10000.0, help='Initial capital')
    parser.add_argument('--strategy', type=str, default='technical',
                       choices=['technical', 'trend_following', 'mean_reversion', 'custom'],
                       help='Strategy to backtest')
    parser.add_argument('--threshold', type=float, default=0.75, help='Signal threshold (0-1)')
    parser.add_argument('--commission', type=float, default=0.0, help='Commission per trade')
    parser.add_argument('--slippage', type=float, default=0.0, help='Slippage per trade (percentage)')
    parser.add_argument('--plot', action='store_true', help='Generate performance charts')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    return parser.parse_args()


def load_historical_data(symbol, days=90):
    """Load historical data from files or data source"""
    
    data_dir = "data/historical"
    
    # Check for cached backtest data to avoid rebuilding every time
    cache_file = f"data/cache/{symbol}_backtest_{days}d.csv"
    if os.path.exists(cache_file):
        try:
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return df
        except Exception as e:
            print(f"Error loading cached data: {e}")
    
    # Try loading from historical files
    historical_files = []
    
    # Look for available historical files
    if os.path.exists(data_dir):
        files = os.listdir(data_dir)
        for file in files:
            if file.startswith(f"{symbol}_daily_") and file.endswith(".csv"):
                historical_files.append(os.path.join(data_dir, file))
    
    if historical_files:
        # Sort files by date (newest first)
        historical_files.sort(reverse=True)
        
        # Try to load the most recent file
        try:
            df = pd.read_csv(historical_files[0])
            
            # If we need more historical data, try loading older files
            for file in historical_files[1:]:
                try:
                    older_df = pd.read_csv(file)
                    # Combine and remove duplicates
                    df = pd.concat([df, older_df]).drop_duplicates()
                except:
                    pass
            
            # Ensure we have enough data
            if len(df) < days:
                print(f"Warning: Only {len(df)} days of data available for {symbol}, need {days}")
        except Exception as e:
            print(f"Error loading historical files for {symbol}: {e}")
            return None
    else:
        # If no files exist, try Yahoo Finance
        try:
            import yfinance as yf
            # Add some buffer days to ensure enough data
            buffer_days = int(days * 1.5)
            df = yf.download(symbol, period=f"{buffer_days}d")
            if df.empty:
                print(f"Error: No data found for {symbol}")
                return None
                
            # Cache this data
            if not os.path.exists("data/cache"):
                os.makedirs("data/cache")
            df.to_csv(cache_file)
        except Exception as e:
            print(f"Error loading data for {symbol}: {e}")
            return None
    
    return df


def run_backtest(data, strategy='technical', initial_capital=10000.0, threshold=0.75, 
                commission=0.0, slippage=0.0, verbose=False):
    """Run a backtest on the given data using the specified strategy"""
    
    if data is None or len(data) < 50:
        print("Error: Not enough data for backtest")
        return None
    
    # Calculate technical indicators
    data = calculate_technical_indicators(data)
    
    # Initialize portfolio variables
    portfolio = {
        'cash': initial_capital,
        'position': 0,
        'position_value': 0.0,
        'total_value': initial_capital,
        'trades': []
    }
    
    # Create results dataframe
    results = pd.DataFrame(index=data.index)
    results['Close'] = data['Close']
    results['Position'] = 0
    results['Cash'] = initial_capital
    results['Holdings'] = 0.0
    results['Total_Value'] = initial_capital
    results['Returns'] = 0.0
    
    # Run simulation day by day
    for i in range(50, len(data)):
        # Current day's data
        current_day = data.iloc[i]
        current_date = data.index[i]
        
        # Previous day's portfolio
        prev_day_idx = i - 1
        portfolio['cash'] = results.iloc[prev_day_idx]['Cash']
        portfolio['position'] = results.iloc[prev_day_idx]['Position']
        portfolio['position_value'] = portfolio['position'] * current_day['Close']
        
        # Generate signals based on data up to (but not including) current day
        if strategy == 'technical':
            signals = generate_signals(data.iloc[:i], data.iloc[i].name, threshold)
            
            # Process signals
            if signals:
                for signal in signals:
                    # Apply trading logic
                    if signal['action'] == 'BUY' and portfolio['position'] <= 0:
                        # Close any short position
                        if portfolio['position'] < 0:
                            # Calculate transaction costs
                            close_value = abs(portfolio['position']) * current_day['Close']
                            transaction_cost = close_value * commission + close_value * slippage
                            
                            # Update portfolio
                            portfolio['cash'] -= close_value + transaction_cost
                            portfolio['position'] = 0
                            
                            # Record trade
                            portfolio['trades'].append({
                                'date': current_date.strftime('%Y-%m-%d'),
                                'action': 'COVER',
                                'price': current_day['Close'],
                                'quantity': abs(portfolio['position']),
                                'value': close_value,
                                'cost': transaction_cost
                            })
                            
                        # Calculate how many shares to buy with 90% of cash
                        cash_to_use = portfolio['cash'] * 0.9
                        shares_to_buy = int(cash_to_use / current_day['Close'])
                        
                        if shares_to_buy > 0:
                            # Calculate transaction costs
                            buy_value = shares_to_buy * current_day['Close']
                            transaction_cost = buy_value * commission + buy_value * slippage
                            
                            # Update portfolio
                            portfolio['cash'] -= buy_value + transaction_cost
                            portfolio['position'] = shares_to_buy
                            
                            # Record trade
                            portfolio['trades'].append({
                                'date': current_date.strftime('%Y-%m-%d'),
                                'action': 'BUY',
                                'price': current_day['Close'],
                                'quantity': shares_to_buy,
                                'value': buy_value,
                                'cost': transaction_cost
                            })
                            
                    elif signal['action'] == 'SELL' and portfolio['position'] >= 0:
                        # Close any long position
                        if portfolio['position'] > 0:
                            # Calculate transaction costs
                            sell_value = portfolio['position'] * current_day['Close']
                            transaction_cost = sell_value * commission + sell_value * slippage
                            
                            # Update portfolio
                            portfolio['cash'] += sell_value - transaction_cost
                            portfolio['position'] = 0
                            
                            # Record trade
                            portfolio['trades'].append({
                                'date': current_date.strftime('%Y-%m-%d'),
                                'action': 'SELL',
                                'price': current_day['Close'],
                                'quantity': portfolio['position'],
                                'value': sell_value,
                                'cost': transaction_cost
                            })
                        
                        # For simplicity, we don't go short in this backtest
        
        # Update portfolio value
        portfolio['position_value'] = portfolio['position'] * current_day['Close']
        portfolio['total_value'] = portfolio['cash'] + portfolio['position_value']
        
        # Update results for this day
        results.loc[current_date, 'Position'] = portfolio['position']
        results.loc[current_date, 'Cash'] = portfolio['cash']
        results.loc[current_date, 'Holdings'] = portfolio['position_value']
        results.loc[current_date, 'Total_Value'] = portfolio['total_value']
        
        # Calculate daily returns
        if i > 50:
            prev_value = results.iloc[i-1]['Total_Value']
            if prev_value > 0:
                daily_return = (portfolio['total_value'] - prev_value) / prev_value
                results.loc[current_date, 'Returns'] = daily_return
    
    # Add cumulative returns
    results['Cumulative_Returns'] = (1 + results['Returns']).cumprod() - 1
    
    # Calculate strategy performance
    performance_metrics = calculate_performance(results, portfolio['trades'])
    
    # Print summary if verbose
    if verbose:
        print("\nBacktest Summary:")
        print(f"Initial Capital: ${initial_capital:.2f}")
        print(f"Final Value: ${results['Total_Value'].iloc[-1]:.2f}")
        print(f"Total Return: {performance_metrics['total_return']:.2f}%")
        print(f"Annualized Return: {performance_metrics['annualized_return']:.2f}%")
        print(f"Sharpe Ratio: {performance_metrics['sharpe']:.2f}")
        print(f"Max Drawdown: {performance_metrics['max_drawdown']:.2f}%")
        print(f"Win Rate: {performance_metrics['win_rate']:.2f}%")
        print(f"Total Trades: {len(portfolio['trades'])}")
    
    # Format for output capture by PowerShell
    print(f"PERFORMANCE: {json.dumps(performance_metrics)}")
    
    return {
        'results': results,
        'trades': portfolio['trades'],
        'performance': performance_metrics
    }


def calculate_performance(results, trades):
    """Calculate performance metrics for the backtest"""
    
    # Basic return metrics
    initial_value = results['Total_Value'].iloc[50]  # Skip warmup period
    final_value = results['Total_Value'].iloc[-1]
    total_return = (final_value - initial_value) / initial_value * 100
    
    # Calculate trading period in years
    days = (results.index[-1] - results.index[50]).days
    years = days / 365.25
    
    # Annualized metrics
    if years > 0:
        annualized_return = ((1 + total_return/100) ** (1/years) - 1) * 100
    else:
        annualized_return = 0
    
    # Risk metrics
    if len(results) > 50:
        daily_returns = results['Returns'].iloc[51:]
        
        # Sharpe ratio (assume risk-free rate of 0 for simplicity)
        sharpe = 0
        if daily_returns.std() > 0:
            sharpe = np.sqrt(252) * daily_returns.mean() / daily_returns.std()
        
        # Maximum drawdown
        cum_returns = (1 + daily_returns).cumprod()
        running_max = cum_returns.cummax()
        drawdown = (cum_returns / running_max - 1) * 100
        max_drawdown = abs(drawdown.min())
        
        # Volatility
        volatility = daily_returns.std() * np.sqrt(252) * 100
    else:
        sharpe = 0
        max_drawdown = 0
        volatility = 0
    
    # Trade metrics
    win_rate = 0
    if len(trades) > 0:
        winning_trades = 0
        for i in range(len(trades)):
            if trades[i]['action'] in ['SELL', 'COVER']:
                # Find the matching entry trade
                entry_trade = None
                for j in range(i-1, -1, -1):
                    if (trades[i]['action'] == 'SELL' and trades[j]['action'] == 'BUY') or \
                       (trades[i]['action'] == 'COVER' and trades[j]['action'] == 'SHORT'):
                        entry_trade = trades[j]
                        break
                
                if entry_trade:
                    # Calculate profit
                    if trades[i]['action'] == 'SELL':
                        profit = trades[i]['price'] - entry_trade['price']
                    else:  # COVER
                        profit = entry_trade['price'] - trades[i]['price']
                    
                    if profit > 0:
                        winning_trades += 1
        
        win_rate = (winning_trades / (len(trades) // 2)) * 100 if len(trades) > 1 else 0
    
    return {
        'total_return': round(total_return, 2),
        'annualized_return': round(annualized_return, 2),
        'sharpe': round(sharpe, 2),
        'max_drawdown': round(max_drawdown, 2),
        'volatility': round(volatility, 2),
        'win_rate': round(win_rate, 2),
        'trade_count': len(trades),
        'period': f"{days} days"
    }


def plot_performance(backtest_results, symbol):
    """Generate performance charts for the backtest"""
    
    results = backtest_results['results']
    trades = backtest_results['trades']
    performance = backtest_results['performance']
    
    # Create a figure with subplots
    fig, axs = plt.subplots(3, 1, figsize=(12, 15), gridspec_kw={'height_ratios': [2, 1, 1]})
    
    # Plot 1: Portfolio value and asset price
    axs[0].plot(results.index, results['Total_Value'], label='Portfolio Value', linewidth=2)
    ax2 = axs[0].twinx()
    ax2.plot(results.index, results['Close'], 'r--', label='Asset Price', alpha=0.7)
    
    # Add buy/sell markers
    for trade in trades:
        date = datetime.strptime(trade['date'], '%Y-%m-%d')
        if date in results.index:
            if trade['action'] == 'BUY':
                axs[0].scatter(date, results.loc[date, 'Total_Value'], 
                               marker='^', color='green', s=100, alpha=0.7)
            elif trade['action'] == 'SELL':
                axs[0].scatter(date, results.loc[date, 'Total_Value'], 
                               marker='v', color='red', s=100, alpha=0.7)
    
    axs[0].set_title(f'{symbol} Backtest Performance')
    axs[0].set_ylabel('Portfolio Value ($)')
    ax2.set_ylabel('Asset Price ($)', color='r')
    axs[0].legend(loc='upper left')
    ax2.legend(loc='upper right')
    axs[0].grid(True)
    
    # Plot 2: Drawdown
    daily_returns = results['Returns'].iloc[51:]
    cum_returns = (1 + daily_returns).cumprod()
    running_max = cum_returns.cummax()
    drawdown = (cum_returns / running_max - 1) * 100
    
    axs[1].fill_between(drawdown.index, drawdown, 0, color='red', alpha=0.3)
    axs[1].plot(drawdown.index, drawdown, color='red', alpha=0.5)
    axs[1].set_ylabel('Drawdown (%)')
    axs[1].axhline(y=0, color='black', linestyle='--', alpha=0.5)
    axs[1].set_ylim(min(drawdown.min() * 1.2, -5), 1)
    axs[1].grid(True)
    
    # Plot 3: Comparison with buy-and-hold
    initial_price = results['Close'].iloc[50]
    final_price = results['Close'].iloc[-1]
    buy_hold_return = (final_price - initial_price) / initial_price * 100
    
    # Normalize both series to start at 100
    strategy_returns = results['Total_Value'].iloc[50:] / results['Total_Value'].iloc[50] * 100
    buy_hold = results['Close'].iloc[50:] / results['Close'].iloc[50] * 100
    
    axs[2].plot(strategy_returns.index, strategy_returns, label=f'Strategy ({performance["total_return"]:.1f}%)', linewidth=2)
    axs[2].plot(buy_hold.index, buy_hold, 'g--', label=f'Buy & Hold ({buy_hold_return:.1f}%)')
    axs[2].set_ylabel('Performance (%)')
    axs[2].legend()
    axs[2].grid(True)
    
    # Add textbox with performance metrics
    textstr = '\n'.join((
        f'Total Return: {performance["total_return"]:.2f}%',
        f'Annualized: {performance["annualized_return"]:.2f}%',
        f'Sharpe Ratio: {performance["sharpe"]:.2f}',
        f'Max Drawdown: {performance["max_drawdown"]:.2f}%',
        f'Win Rate: {performance["win_rate"]:.2f}%',
        f'Trade Count: {performance["trade_count"]}'))
    
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    axs[0].text(0.02, 0.96, textstr, transform=axs[0].transAxes, fontsize=10,
                verticalalignment='top', bbox=props)
    
    plt.tight_layout()
    
    # Save the plot to a file
    timestamp = datetime.now().strftime('%Y%m%d')
    output_dir = 'data/backtests'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    plt.savefig(f'{output_dir}/{symbol}_backtest_{timestamp}.png')
    
    print(f"Backtest performance plot saved to {output_dir}/{symbol}_backtest_{timestamp}.png")
    
    # Save detailed results to CSV
    results.to_csv(f'{output_dir}/{symbol}_backtest_results_{timestamp}.csv')
    
    # Save trades to CSV
    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        trades_df.to_csv(f'{output_dir}/{symbol}_backtest_trades_{timestamp}.csv', index=False)


def main():
    """Main function"""
    args = setup_args()
    
    # Create output directory if it doesn't exist
    if not os.path.exists('data/backtests'):
        os.makedirs('data/backtests')
    
    # Run backtest for each symbol
    for symbol in args.symbols:
        if args.verbose:
            print(f"\nBacktesting strategy for {symbol}...")
        
        # Load data
        data = load_historical_data(symbol, args.days)
        
        if data is None:
            print(f"Error: Could not load data for {symbol}")
            continue
        
        # Run backtest
        backtest_results = run_backtest(
            data=data,
            strategy=args.strategy,
            initial_capital=args.initial_capital,
            threshold=args.threshold,
            commission=args.commission,
            slippage=args.slippage,
            verbose=args.verbose
        )
        
        if backtest_results is None:
            print(f"Error: Backtest failed for {symbol}")
            continue
        
        # Plot results if requested
        if args.plot:
            plot_performance(backtest_results, symbol)
    
    print("\nBacktesting completed.")


if __name__ == "__main__":
    main() 