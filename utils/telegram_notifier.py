"""
Telegram 通知器
"""

import os
import sys

# 优先导入imghdr兼容性模块，确保所有后续导入的模块都能正常使用imghdr
try:
    import imghdr_compatibility  # 这会自动注册PIL基于的imghdr替代品
except ImportError:
    print("⚠️ 警告: 无法加载imghdr_compatibility模块，尝试备用方案")
    # 如果imghdr_compatibility不存在，保留现有的兼容层
    try:
        import PIL_image_check  # 这会自动替代imghdr模块
    except ImportError:
        # 如果PIL_image_check不存在，手动创建兼容层
        try:
            from PIL import Image
            
            # 创建imghdr兼容模块
            class ImghdrModule:
                @staticmethod
                def what(file, h=None):
                    try:
                        if isinstance(file, str):
                            with Image.open(file) as img:
                                return img.format.lower() if img.format else None
                        else:
                            pos = file.tell()
                            file.seek(0)
                            with Image.open(file) as img:
                                format = img.format
                            file.seek(pos)
                            return format.lower() if format else None
                    except Exception:
                        return None
                
                # 添加测试函数兼容性
                tests = {
                    'jpeg': lambda f: ImghdrModule.what(f) == 'jpeg',
                    'png': lambda f: ImghdrModule.what(f) == 'png',
                    'gif': lambda f: ImghdrModule.what(f) == 'gif',
                    'bmp': lambda f: ImghdrModule.what(f) == 'bmp',
                }
            
            # 注册到系统模块
            sys.modules['imghdr'] = ImghdrModule()
        except ImportError:
            print("⚠️ 警告: 无法加载PIL，请安装: pip install pillow")

import io
import logging
import requests
from typing import Optional, Union, Dict, List
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
import json
import seaborn as sns
from datetime import datetime
import time
import shutil
from requests.exceptions import RequestException
import plotly.graph_objects as go

class TelegramNotifier:
    """Telegram 通知器"""
    
    def __init__(self, token: Optional[str] = None):
        """
        初始化 Telegram 通知器
        Args:
            token: Telegram Bot Token，如果不提供则从环境变量读取
        """
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            logging.warning("未设置 TELEGRAM_BOT_TOKEN 环境变量，Telegram 通知功能将被禁用")
            return
            
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not self.chat_id:
            print("⚠️ Warning: TELEGRAM_CHAT_ID not set in .env")
        
        # Create temp directory for charts if it doesn't exist
        self.temp_dir = Path("temp_charts")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Rate limiting parameters
        self.last_request_time = 0
        self.min_request_interval = 1/30  # Maximum 30 messages per second
        
        # Clean up old temp files on initialization
        self._cleanup_old_files()
    
    def _rate_limit(self):
        """Implement rate limiting for Telegram API requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _cleanup_old_files(self, max_age_hours: int = 24):
        """Clean up old chart files from the temp directory."""
        try:
            current_time = datetime.now()
            for file in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, file)
                if os.path.isfile(file_path):
                    # Get file's last modification time
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    # If file is older than max_age_hours, delete it
                    if (current_time - file_time).total_seconds() > (max_age_hours * 3600):
                        try:
                            os.remove(file_path)
                        except OSError:
                            continue
        except Exception as e:
            print(f"⚠️ Warning: Error during file cleanup: {e}")
    
    def send_message(self, text: str) -> bool:
        """
        发送文本消息
        Args:
            text: 要发送的文本
        Returns:
            是否发送成功
        """
        if not self.token or not self.chat_id:
            return False
            
        try:
            # Apply rate limiting
            self._rate_limit()
            
            # Send message via HTTP API
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logging.error(f"发送Telegram消息失败: {str(e)}")
            return False
    
    def send_image(self, 
                  fig: plt.Figure,
                  caption: Optional[str] = None) -> bool:
        """
        发送图片
        Args:
            fig: matplotlib图表
            caption: 图片说明文字
        Returns:
            是否发送成功
        """
        if not self.token or not self.chat_id:
            return False
            
        try:
            # Apply rate limiting
            self._rate_limit()
            
            # 将图表转换为字节流
            buf = io.BytesIO()
            fig.savefig(buf, format='png')
            buf.seek(0)
            
            # Send photo via HTTP API
            url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
            
            # Prepare files and data
            files = {
                "photo": ("chart.png", buf, "image/png")
            }
            
            data = {
                "chat_id": self.chat_id
            }
            
            if caption:
                data["caption"] = caption
            
            response = requests.post(url, files=files, data=data, timeout=20)
            response.raise_for_status()
            return True
        except Exception as e:
            logging.error(f"发送Telegram图片失败: {str(e)}")
            return False
    
    def send_candlestick_chart(self,
                           df: pd.DataFrame,
                           title: str = "",
                           indicators: Optional[Dict] = None) -> Dict:
        """Send a candlestick chart with optional indicators."""
        try:
            # Create temp directory if it doesn't exist
            os.makedirs(self.temp_dir, exist_ok=True)
            
            # Generate a unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chart_path = os.path.join(self.temp_dir, f"chart_{timestamp}.png")
            
            # Create the candlestick chart
            fig = go.Figure(data=[go.Candlestick(x=df.index,
                                               open=df['Open'],
                                               high=df['High'],
                                               low=df['Low'],
                                               close=df['Close'])])
            
            # Add indicators if provided
            if indicators:
                for name, data in indicators.items():
                    fig.add_trace(go.Scatter(x=df.index, y=data, name=name))
            
            # Update layout
            fig.update_layout(title=title,
                            yaxis_title='Price',
                            template='plotly_dark',
                            height=800)
            
            # Save the chart
            fig.write_image(chart_path)
            
            # Send the chart
            result = self.send_image(fig)
            
            # Clean up the file and old files
            try:
                os.remove(chart_path)
                self._cleanup_old_files()
            except OSError as e:
                print(f"⚠️ Warning: Could not clean up chart file: {e}")
            
            return result
            
        except (ValueError, AttributeError) as e:
            error_msg = f"❌ Error creating chart - Invalid data format: {e}"
            print(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"❌ Unexpected error creating/sending chart: {e}"
            print(error_msg)
            return {"error": error_msg}
    
    def send_pnl_chart(self,
                       pnl_data: pd.Series,
                       title: str = "PnL Performance") -> Dict:
        """Send a PnL performance chart."""
        plt.figure(figsize=(12, 6))
        
        # Create cumulative PnL line
        cum_pnl = pnl_data.cumsum()
        plt.plot(cum_pnl.index, cum_pnl.values, 'b-', label='Cumulative PnL')
        
        # Add drawdown shading
        running_max = cum_pnl.expanding(min_periods=1).max()
        drawdown = cum_pnl - running_max
        plt.fill_between(drawdown.index, drawdown.values, 0, 
                        color='red', alpha=0.3, label='Drawdown')
        
        plt.title(title)
        plt.xlabel('Date')
        plt.ylabel('PnL ($)')
        plt.legend()
        plt.grid(True)
        
        # Save to temp file
        temp_file = self.temp_dir / f"pnl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(temp_file)
        plt.close()
        
        return self.send_image(plt.gcf(), caption=title)
    
    def send_technical_indicators(self,
                                data: pd.DataFrame,
                                indicators: Dict[str, pd.Series]) -> Dict:
        """Send technical indicators chart."""
        fig, axes = plt.subplots(len(indicators) + 1, 1, figsize=(12, 4*len(indicators)))
        
        # Plot price in the first subplot
        axes[0].plot(data.index, data['close'], label='Price')
        axes[0].set_title('Price')
        axes[0].grid(True)
        
        # Plot each indicator
        for i, (name, series) in enumerate(indicators.items(), 1):
            axes[i].plot(series.index, series.values, label=name)
            axes[i].set_title(name)
            axes[i].grid(True)
            axes[i].legend()
        
        plt.tight_layout()
        
        # Save to temp file
        temp_file = self.temp_dir / f"indicators_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(temp_file)
        plt.close()
        
        return self.send_image(fig, caption="Technical Indicators")
    
    def send_market_status(self,
                          data: pd.DataFrame,
                          window: int = 20) -> Dict:
        """Send current market status with key metrics."""
        current_price = data['close'].iloc[-1]
        sma = data['close'].rolling(window=window).mean().iloc[-1]
        volatility = data['close'].pct_change().std() * np.sqrt(252)
        rsi = self._calculate_rsi(data['close']).iloc[-1]
        
        status = (
            f"📊 <b>Market Status Update</b>\n\n"
            f"Current Price: ${current_price:,.2f}\n"
            f"SMA({window}): ${sma:,.2f}\n"
            f"Trend: {'🟢 Bullish' if current_price > sma else '🔴 Bearish'}\n"
            f"Volatility (Ann.): {volatility:.2%}\n"
            f"RSI: {rsi:.1f}"
        )
        
        return self.send_message(status)
    
    def send_indicator_alert(self,
                           indicator_name: str,
                           current_value: float,
                           threshold: float,
                           direction: str) -> Dict:
        """Send technical indicator alert."""
        emoji = "🟢" if direction.lower() == "above" else "🔴"
        
        alert = (
            f"{emoji} <b>Indicator Alert</b>\n\n"
            f"Indicator: {indicator_name}\n"
            f"Current Value: {current_value:.2f}\n"
            f"Threshold: {threshold:.2f}\n"
            f"Direction: {direction.upper()}"
        )
        
        return self.send_message(alert)
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI technical indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def send_trade_alert(self, 
                        action: str, 
                        symbol: str, 
                        price: float, 
                        quantity: float,
                        pnl: Optional[float] = None) -> Dict:
        """Send a trade execution alert."""
        emoji = "🟢" if action.lower() == "buy" else "🔴"
        
        message = (
            f"{emoji} <b>Trade Alert</b>\n\n"
            f"Action: {action.upper()}\n"
            f"Symbol: {symbol}\n"
            f"Price: ${price:,.2f}\n"
            f"Quantity: {quantity:,.2f}"
        )
        
        if pnl is not None:
            message += f"\nPnL: ${pnl:,.2f}"
        
        return self.send_message(message)
    
    def send_risk_alert(self, 
                        rule_name: str, 
                        message: str,
                        current_value: float,
                        threshold: float) -> Dict:
        """Send a risk rule violation alert."""
        alert = (
            f"⚠️ <b>Risk Alert</b>\n\n"
            f"Rule: {rule_name}\n"
            f"Message: {message}\n"
            f"Current Value: {current_value:.2f}\n"
            f"Threshold: {threshold:.2f}"
        )
        return self.send_message(alert)
    
    def send_performance_report(self,
                              total_return: float,
                              sharpe_ratio: float,
                              max_drawdown: float,
                              win_rate: float) -> Dict:
        """Send a performance metrics report."""
        report = (
            f"📊 <b>Performance Report</b>\n\n"
            f"Total Return: {total_return:.2%}\n"
            f"Sharpe Ratio: {sharpe_ratio:.2f}\n"
            f"Max Drawdown: {max_drawdown:.2%}\n"
            f"Win Rate: {win_rate:.2%}"
        )
        return self.send_message(report)

# Create a global instance
notifier = TelegramNotifier()

if __name__ == "__main__":
    # Test the notification system
    notifier.send_message("🤖 Bot is online and ready!")
    
    # Test with sample data
    dates = pd.date_range(start='2024-01-01', periods=100)
    data = pd.DataFrame({
        'open': np.random.normal(100, 2, 100),
        'high': np.random.normal(102, 2, 100),
        'low': np.random.normal(98, 2, 100),
        'close': np.random.normal(101, 2, 100),
        'volume': np.random.normal(1000000, 200000, 100)
    }, index=dates)
    
    # Test candlestick chart
    trades = [
        {'action': 'BUY', 'index': dates[10], 'price': 101},
        {'action': 'SELL', 'index': dates[20], 'price': 103}
    ]
    notifier.send_candlestick_chart(data, trades=trades)
    
    # Test PnL chart
    pnl = pd.Series(np.random.normal(0.001, 0.01, 100).cumsum(), index=dates)
    notifier.send_pnl_chart(pnl)
    
    # Test technical indicators
    indicators = {
        'SMA(20)': data['close'].rolling(20).mean(),
        'RSI': notifier._calculate_rsi(data['close'])
    }
    notifier.send_technical_indicators(data, indicators)
    
    # Test market status
    notifier.send_market_status(data)
    
    # Test indicator alert
    notifier.send_indicator_alert('RSI', 75.5, 70, 'above') 