#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
standalone_google_finance.py - 独立的Google Finance数据获取工具

用于替代IBKR数据源，提供实时和历史市场数据获取功能，同时支持期权数据和回测功能
"""

import os
import sys
import json
import time
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging

# 导入Google Finance API（首先尝试从本地导入，如果失败则使用已安装的模块）
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'googlefinance-master'))
    from googlefinance import getQuotes, getNews
    print("成功从本地导入Google Finance库")
except ImportError:
    try:
        # 尝试从已安装的模块导入
        from googlefinance import getQuotes, getNews
        print("成功从已安装模块导入Google Finance库")
    except ImportError:
        print("Google Finance库导入失败，将使用备用数据源")
        # 如果Google Finance库不可用，使用备用数据源
        try:
            import yfinance as yf
            print("使用Yahoo Finance作为备用数据源")
        except ImportError:
            print("请安装所需依赖: pip install googlefinance-api yfinance pandas matplotlib")
            sys.exit(1)

# 导入自定义Google Finance数据API（如果存在）
try:
    from google_finance_data import GoogleFinanceAPI
    USE_EXTENDED_API = True
    print("使用扩展的Google Finance API")
except ImportError:
    USE_EXTENDED_API = False
    print("未找到扩展的Google Finance API，使用基础功能")

# 设置日志
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/google_finance_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GoogleFinance")

# 确保数据目录存在
data_dir = "data/historical"
if not os.path.exists(data_dir):
    os.makedirs(data_dir, exist_ok=True)

def get_real_time_data(symbols):
    """获取实时市场数据"""
    if isinstance(symbols, str):
        symbols = [symbols]
    
    try:
        if USE_EXTENDED_API:
            # 使用扩展API
            api = GoogleFinanceAPI()
            quotes = api.get_real_time_quotes(symbols)
            return quotes
        else:
            # 使用基础Google Finance API
            try:
                quotes = getQuotes(symbols)
                return quotes
            except Exception as e:
                logger.warning(f"Google Finance API失败: {e}，使用备用数据源")
                # 使用YFinance作为备用
                data = yf.download(symbols, period="1d", interval="1m", group_by="ticker", progress=False)
                result = []
                
                for symbol in symbols:
                    if len(symbols) > 1:
                        if symbol in data.columns.levels[0]:
                            latest = data[symbol].iloc[-1].to_dict()
                    else:
                        latest = data.iloc[-1].to_dict()
                    
                    result.append({
                        "StockSymbol": symbol,
                        "LastTradePrice": str(latest.get("Close", "N/A")),
                        "LastTradeTime": datetime.now().strftime("%I:%M%p %Z"),
                        "LastTradeDateTimeLong": datetime.now().strftime("%b %d, %I:%M%p %Z"),
                        "Change": str(latest.get("Close", 0) - latest.get("Open", 0)),
                        "ChangePercent": str(round((latest.get("Close", 0) / latest.get("Open", 0) - 1) * 100, 2)) if latest.get("Open", 0) else "0",
                        "Index": "UNKNOWN"  # Yahoo不提供这个信息
                    })
                return result
    except Exception as e:
        logger.error(f"获取实时数据失败: {e}")
        return None

def get_historical_data(symbol, days=30, interval="1d", save_csv=True, plot=False):
    """获取历史市场数据"""
    period = f"{days}d"
    
    try:
        if USE_EXTENDED_API:
            # 使用扩展API
            api = GoogleFinanceAPI()
            df = api.get_historical_data(symbol, period=period, interval=interval)
        else:
            # 使用YFinance作为数据源
            df = yf.download(symbol, period=period, interval=interval, progress=False)
        
        if df is None or df.empty:
            logger.error(f"无法获取{symbol}的历史数据")
            return None
        
        # 保存到CSV
        if save_csv:
            filename = f"{data_dir}/{symbol}_{interval}_{datetime.now().strftime('%Y%m%d')}.csv"
            df.to_csv(filename)
            logger.info(f"历史数据已保存到 {filename}")
        
        # 绘制图表
        if plot:
            plt.figure(figsize=(12, 6))
            plt.plot(df.index, df['Close'], label=f'{symbol} 收盘价')
            plt.title(f"{symbol} 历史价格 - {period}")
            plt.xlabel("日期")
            plt.ylabel("价格")
            plt.legend()
            plt.grid(True)
            
            # 保存图表
            plot_filename = f"{data_dir}/{symbol}_{interval}_{datetime.now().strftime('%Y%m%d')}.png"
            plt.savefig(plot_filename)
            logger.info(f"价格图表已保存到 {plot_filename}")
            
            if 'sys.ps1' in sys.__dict__:  # 在交互式环境中显示图表
                plt.show()
        
        return df
    
    except Exception as e:
        logger.error(f"获取历史数据失败: {e}")
        return None

def get_options_data(symbol):
    """获取期权数据"""
    try:
        if USE_EXTENDED_API:
            # 使用扩展API
            api = GoogleFinanceAPI()
            options_data = api.get_options_chain(symbol)
            
            if options_data:
                # 保存到JSON
                filename = f"{data_dir}/{symbol}_options_{datetime.now().strftime('%Y%m%d')}.json"
                with open(filename, 'w') as f:
                    json.dump(options_data, f, indent=2)
                logger.info(f"期权数据已保存到 {filename}")
                
                # 显示信息
                expiry_dates = list(options_data.keys())
                logger.info(f"{symbol} 可用期权到期日: {expiry_dates}")
                
                # 取第一个到期日的数据作为示例
                if expiry_dates:
                    first_expiry = expiry_dates[0]
                    call_count = len(options_data[first_expiry]["calls"])
                    put_count = len(options_data[first_expiry]["puts"])
                    logger.info(f"到期日 {first_expiry}: {call_count} 个看涨期权, {put_count} 个看跌期权")
                
                return options_data
            else:
                logger.warning(f"{symbol} 没有可用的期权数据")
                return None
        else:
            # 使用YFinance获取期权数据
            ticker = yf.Ticker(symbol)
            expiry_dates = ticker.options
            
            if not expiry_dates:
                logger.warning(f"{symbol} 没有可用的期权数据")
                return None
            
            options_data = {}
            for date in expiry_dates:
                opt = ticker.option_chain(date)
                options_data[date] = {
                    "calls": opt.calls.to_dict('records'),
                    "puts": opt.puts.to_dict('records')
                }
            
            # 保存到JSON
            filename = f"{data_dir}/{symbol}_options_{datetime.now().strftime('%Y%m%d')}.json"
            with open(filename, 'w') as f:
                json.dump(options_data, f, indent=2)
            logger.info(f"期权数据已保存到 {filename}")
            
            # 显示信息
            logger.info(f"{symbol} 可用期权到期日: {expiry_dates}")
            
            # 取第一个到期日的数据作为示例
            if expiry_dates:
                first_expiry = expiry_dates[0]
                call_count = len(options_data[first_expiry]["calls"])
                put_count = len(options_data[first_expiry]["puts"])
                logger.info(f"到期日 {first_expiry}: {call_count} 个看涨期权, {put_count} 个看跌期权")
            
            return options_data
    
    except Exception as e:
        logger.error(f"获取期权数据失败: {e}")
        return None

def get_market_news(symbol=None, count=5):
    """获取市场新闻"""
    try:
        if symbol:
            if USE_EXTENDED_API and hasattr(GoogleFinanceAPI, 'get_market_news'):
                # 使用扩展API
                api = GoogleFinanceAPI()
                news = api.get_market_news(symbol, count)
            else:
                # 使用基础Google Finance API
                try:
                    news = getNews(symbol)
                    if news and len(news) > count:
                        news = news[:count]
                except Exception as e:
                    logger.warning(f"获取{symbol}新闻失败: {e}")
                    news = []
            
            # 显示新闻
            logger.info(f"{symbol} 最新新闻:")
            for i, item in enumerate(news, 1):
                title = item.get('t', item.get('title', 'No title'))
                date = item.get('d', item.get('date', 'No date'))
                url = item.get('u', item.get('url', 'No URL'))
                logger.info(f"{i}. {title} ({date}) - {url}")
            
            return news
        else:
            logger.warning("没有指定股票代码，无法获取相关新闻")
            return None
    
    except Exception as e:
        logger.error(f"获取市场新闻失败: {e}")
        return None

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Google Finance 数据获取工具')
    parser.add_argument('--symbol', type=str, help='股票代码')
    parser.add_argument('--symbols', type=str, help='多个股票代码，逗号分隔')
    parser.add_argument('--realtime', action='store_true', help='获取实时数据')
    parser.add_argument('--historical', action='store_true', help='获取历史数据')
    parser.add_argument('--options', action='store_true', help='获取期权数据')
    parser.add_argument('--news', action='store_true', help='获取市场新闻')
    parser.add_argument('--days', type=int, default=30, help='历史数据天数')
    parser.add_argument('--timeframe', type=str, default='1d', help='时间周期：1m, 2m, 5m, 15m, 30m, 60m, 1h, 1d, 1wk, 1mo')
    parser.add_argument('--plot', action='store_true', help='绘制图表')
    parser.add_argument('--save', action='store_true', help='保存数据为CSV')
    
    args = parser.parse_args()
    
    # 处理股票代码
    symbols = []
    if args.symbol:
        symbols = [args.symbol]
    elif args.symbols:
        symbols = args.symbols.split(',')
    else:
        symbols = ['SPY']  # 默认使用SPY
    
    print(f"正在处理股票: {', '.join(symbols)}")
    
    # 如果没有指定任何操作，则默认获取实时数据
    if not (args.realtime or args.historical or args.options or args.news):
        args.realtime = True
    
    # 获取实时数据
    if args.realtime:
        print("\n获取实时数据:")
        quotes = get_real_time_data(symbols)
        if quotes:
            for quote in quotes:
                print(f"股票: {quote.get('StockSymbol', '-')}")
                print(f"价格: {quote.get('LastTradePrice', '-')}")
                print(f"时间: {quote.get('LastTradeTime', '-')}")
                print(f"变化: {quote.get('Change', '-')} ({quote.get('ChangePercent', '-')}%)")
                print(f"交易所: {quote.get('Index', '-')}")
                print("-----")
    
    # 获取历史数据
    if args.historical:
        print("\n获取历史数据:")
        for symbol in symbols:
            print(f"处理 {symbol} 的历史数据...")
            df = get_historical_data(symbol, days=args.days, interval=args.timeframe, 
                                    save_csv=args.save, plot=args.plot)
            if df is not None:
                print(f"获取了 {len(df)} 条历史记录")
                print(df.tail(5))  # 显示最近5条数据
                print("-----")
    
    # 获取期权数据
    if args.options:
        print("\n获取期权数据:")
        for symbol in symbols:
            print(f"处理 {symbol} 的期权数据...")
            options = get_options_data(symbol)
            if options:
                expiry_dates = list(options.keys())
                print(f"可用到期日: {expiry_dates}")
                print("-----")
    
    # 获取市场新闻
    if args.news:
        print("\n获取市场新闻:")
        for symbol in symbols:
            print(f"获取 {symbol} 的相关新闻...")
            get_market_news(symbol, count=5)
            print("-----")
    
if __name__ == "__main__":
    main() 