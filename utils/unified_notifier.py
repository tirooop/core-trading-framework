"""
统一通知接口，支持同时向 Telegram 和飞书发送消息
"""

import os
import logging
from typing import Optional, Dict, List, Union, Any
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import mplfinance as mpf
from io import BytesIO
from dataclasses import dataclass
import json
import requests
from dotenv import load_dotenv

from utils.telegram_notifier import TelegramNotifier
from utils.feishu_notifier import FeishuNotifier

load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class NotificationConfig:
    """Configuration for notification system"""
    telegram_enabled: bool = False
    feishu_enabled: bool = False
    telegram_chat_id: Optional[str] = None
    telegram_token: Optional[str] = None
    feishu_webhook: Optional[str] = None
    min_confidence: float = 0.7

class UnifiedNotifier:
    """Unified notification system supporting multiple channels"""
    
    def __init__(self, config: Optional[NotificationConfig] = None):
        # Check if tokens are available
        telegram_token = os.getenv("TELEGRAM_TOKEN")
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        # Only enable Telegram if explicitly requested via env var AND tokens are available
        telegram_enabled = bool(os.getenv("TELEGRAM_ENABLED", "false").lower() == "true")
        if telegram_enabled and (not telegram_token or not telegram_chat_id):
            logger.warning("未设置 TELEGRAM_BOT_TOKEN 环境变量，Telegram 通知功能将被禁用")
            telegram_enabled = False
        
        self.config = config or NotificationConfig(
            telegram_enabled=telegram_enabled,
            feishu_enabled=bool(os.getenv("FEISHU_ENABLED", "false").lower() == "true"),
            telegram_chat_id=telegram_chat_id,
            telegram_token=telegram_token,
            feishu_webhook=os.getenv("FEISHU_WEBHOOK"),
            min_confidence=float(os.getenv("MIN_CONFIDENCE", "0.7"))
        )
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate notification configuration"""
        if self.config.telegram_enabled:
            if not self.config.telegram_token:
                raise ValueError("Telegram token is required when Telegram is enabled")
            if not self.config.telegram_chat_id:
                raise ValueError("Telegram chat ID is required when Telegram is enabled")
        
        if self.config.feishu_enabled:
            if not self.config.feishu_webhook:
                raise ValueError("Feishu webhook URL is required when Feishu is enabled")
    
    def send_option_entry_signal(self, 
                               symbol: str,
                               analysis_result: Dict,
                               fusion_result: Dict):
        """
        Send option entry signal notification
        
        Args:
            symbol: Trading symbol
            analysis_result: Analysis result from AIAnalyst
            fusion_result: Fused signal result
        """
        if fusion_result['confidence'] < self.config.min_confidence:
            logger.info(f"Skipping notification for {symbol} due to low confidence")
            return
        
        # Format message
        message = self._format_option_signal(symbol, analysis_result, fusion_result)
        
        # Send to enabled channels
        if self.config.telegram_enabled:
            self._send_telegram(message)
        
        if self.config.feishu_enabled:
            self._send_feishu(message)
    
    def _format_option_signal(self,
                            symbol: str,
                            analysis_result: Dict,
                            fusion_result: Dict) -> str:
        """Format option signal message"""
        # Extract key information
        direction = fusion_result['action']
        confidence = fusion_result['confidence']
        risk_level = fusion_result['risk_level']
        
        # Format message
        message = f"🚨 *{symbol} Option Signal*\n\n"
        message += f"Direction: {direction}\n"
        message += f"Confidence: {confidence:.2%}\n"
        message += f"Risk Level: {risk_level}\n\n"
        
        # Add reasoning
        message += "*Reasoning:*\n"
        for factor in fusion_result['factor_scores']:
            message += f"• {factor['name']}: {factor['description']}\n"
        
        # Add recommendations
        message += "\n*Recommendations:*\n"
        message += fusion_result['recommendation']
        
        return message
    
    def _send_telegram(self, message: str):
        """Send message to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.config.telegram_token}/sendMessage"
            data = {
                "chat_id": self.config.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, json=data)
            response.raise_for_status()
            logger.info("Successfully sent Telegram notification")
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {str(e)}")
    
    def _send_feishu(self, message: str):
        """Send message to Feishu"""
        try:
            data = {
                "msg_type": "text",
                "content": {
                    "text": message
                }
            }
            response = requests.post(self.config.feishu_webhook, json=data)
            response.raise_for_status()
            logger.info("Successfully sent Feishu notification")
        except Exception as e:
            logger.error(f"Error sending Feishu notification: {str(e)}")
    
    def send_error_notification(self, error: str, context: Optional[Dict] = None):
        """Send error notification"""
        message = f"❌ *Error Alert*\n\n{error}"
        if context:
            message += f"\n\nContext: {json.dumps(context, indent=2)}"
        
        if self.config.telegram_enabled:
            self._send_telegram(message)
        
        if self.config.feishu_enabled:
            self._send_feishu(message)
    
    def send_system_status(self, status: Dict):
        """Send system status notification"""
        message = "📊 *System Status*\n\n"
        for key, value in status.items():
            message += f"{key}: {value}\n"
        
        if self.config.telegram_enabled:
            self._send_telegram(message)
        
        if self.config.feishu_enabled:
            self._send_feishu(message)

    def send_message(self, message: str, title: str = "通知") -> Dict[str, Any]:
        """Send a text message through all configured channels."""
        results = {}
        
        if self.config.feishu_enabled:
            try:
                results["feishu"] = self._send_feishu(message)
            except Exception as e:
                logging.error(f"Failed to send message via Feishu: {e}")
                results["feishu"] = {"error": str(e)}
        
        if self.config.telegram_enabled:
            try:
                results["telegram"] = self._send_telegram(message)
            except Exception as e:
                logging.error(f"Failed to send message via Telegram: {e}")
                results["telegram"] = {"error": str(e)}
        
        return results

    def send_image(self, fig: plt.Figure, caption: str = "图表") -> None:
        """发送图表到所有启用的渠道"""
        if self.config.telegram_enabled:
            self._send_telegram(f"{caption}\n{fig}")
        if self.config.feishu_enabled:
            self._send_feishu(f"{caption}\n{fig}")

    def send_market_analysis(self, symbol: str, trend: str, volatility: str, 
                           sentiment: str, support: float = None, 
                           resistance: float = None) -> Dict[str, Any]:
        """Send a market analysis report through all configured channels."""
        title = f"📊 Market Analysis - {symbol}"
        message = f"Symbol: {symbol}\n"
        message += f"Trend: {trend}\n"
        message += f"Volatility: {volatility}\n"
        message += f"Sentiment: {sentiment}\n"
        
        if support:
            message += f"Support Level: {support}\n"
        if resistance:
            message += f"Resistance Level: {resistance}\n"
            
        return self.send_message(message, title)

    def send_option_chain_analysis(self, symbol: str, expiry: str, 
                                 volume_analysis: Dict[str, Any],
                                 call_put_ratio: float) -> Dict[str, Any]:
        """Send an option chain analysis report through all configured channels."""
        title = f"🔍 Option Chain Analysis - {symbol}"
        message = f"Symbol: {symbol}\n"
        message += f"Expiry: {expiry}\n"
        message += f"Call/Put Ratio: {call_put_ratio:.2f}\n\n"
        
        message += "Volume Analysis:\n"
        for key, value in volume_analysis.items():
            message += f"{key}: {value}\n"
            
        return self.send_message(message, title)

    def send_training_update(self, episode: int, reward: float, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Send a training progress update through all configured channels."""
        title = f"🤖 Training Update - Episode {episode}"
        message = f"Reward: {reward:.2f}\n\n"
        
        message += "Metrics:\n"
        for metric_name, metric_value in metrics.items():
            message += f"{metric_name}: {metric_value:.4f}\n"
            
        return self.send_message(message, title)

    def send_candlestick_chart(self, df: pd.DataFrame, title: str = "Price Chart") -> Dict[str, Any]:
        """
        Send a candlestick chart through all configured channels.
        
        Args:
            df: DataFrame with columns: Open, High, Low, Close, Volume
            title: Chart title
        """
        results = {}
        
        # Create candlestick chart
        fig, ax = plt.subplots(figsize=(10, 6))
        mpf.plot(df, type='candle', style='charles',
                title=title,
                ylabel='Price',
                volume=True,
                figsize=(10, 6))
        
        # Save plot to buffer
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        # Send through configured channels
        if self.config.feishu_enabled:
            try:
                results["feishu"] = self._send_feishu(f"{title}\n{fig}")
            except Exception as e:
                logging.error(f"Failed to send chart via Feishu: {e}")
                results["feishu"] = {"error": str(e)}
        
        if self.config.telegram_enabled:
            try:
                results["telegram"] = self._send_telegram(f"{title}\n{fig}")
            except Exception as e:
                logging.error(f"Failed to send chart via Telegram: {e}")
                results["telegram"] = {"error": str(e)}
        
        return results

    def send_training_complete(self,
                             total_steps: int,
                             final_metrics: Dict[str, float],
                             model_path: str) -> None:
        """发送训练完成通知"""
        metrics_str = "\n".join([f"• {k}: {v:.4f}" for k, v in final_metrics.items()])
        msg = (
            f"✅ 训练完成!\n\n"
            f"总步数: {total_steps}\n"
            f"最终指标:\n{metrics_str}\n\n"
            f"模型保存路径: {model_path}"
        )
        self.send_message(msg, "训练完成") 