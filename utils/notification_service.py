from typing import Dict, Any, List, Optional
import requests
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

class NotificationService:
    """通知服务，用于发送交易信号"""
    
    def __init__(self):
        load_dotenv()
        
        # 加载配置
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        self.email_sender = os.getenv('EMAIL_SENDER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.email_receiver = os.getenv('EMAIL_RECEIVER')
        self.email_smtp_server = os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
        self.email_smtp_port = int(os.getenv('EMAIL_SMTP_PORT', '587'))
        
        # 检查配置
        self.telegram_enabled = bool(self.telegram_token and self.telegram_chat_id)
        self.email_enabled = bool(self.email_sender and self.email_password and self.email_receiver)
    
    def _format_signal_message(self, signal: Dict[str, Any], include_backtest: bool = True) -> str:
        """格式化信号消息"""
        try:
            # 基本信息
            symbol = signal.get('symbol', 'Unknown')
            bias = signal.get('bias', 'NEUTRAL')
            signal_type = signal.get('signal_type', 'WEAK')
            signal_strength = signal.get('signal_strength', 0)
            suggested_strategy = signal.get('suggested_strategy', {})
            
            # 构建消息
            message = f"🔔 *交易信号 - {symbol}*\n\n"
            
            # 方向和强度
            bias_emoji = "🔼" if bias == "BULLISH" else "🔽" if bias == "BEARISH" else "➡️"
            message += f"{bias_emoji} *方向*: {bias}\n"
            message += f"🔋 *信号强度*: {signal_strength:.2f}\n"
            message += f"📊 *信号类型*: {signal_type}\n\n"
            
            # 建议策略
            if suggested_strategy:
                strategy_type = suggested_strategy.get('type', 'Unknown')
                strike = suggested_strategy.get('strike', 0)
                expiration_days = suggested_strategy.get('expiration_days', 0)
                reason = suggested_strategy.get('reason', '')
                
                message += f"📈 *建议策略*: {strategy_type}\n"
                message += f"💰 *执行价*: {strike}\n"
                message += f"📅 *到期日*: {expiration_days} 天\n"
                message += f"📝 *理由*: {reason}\n\n"
            
            # 逻辑链
            logic_chain = signal.get('logic_chain', [])
            if logic_chain:
                message += "🧠 *分析逻辑*:\n"
                for i, logic in enumerate(logic_chain, 1):
                    message += f"{i}. {logic}\n"
                message += "\n"
            
            # 风险因素
            risk_factors = signal.get('risk_factors', [])
            if risk_factors:
                message += "⚠️ *风险因素*:\n"
                for i, risk in enumerate(risk_factors, 1):
                    message += f"{i}. {risk}\n"
                message += "\n"
            
            # 回测结果
            backtest_results = signal.get('backtest_results', {})
            if include_backtest and backtest_results:
                message += "📊 *回测结果*:\n"
                message += f"📈 总收益: {backtest_results.get('total_return', 0):.2%}\n"
                message += f"📊 年化收益: {backtest_results.get('annualized_return', 0):.2%}\n"
                message += f"📉 最大回撤: {backtest_results.get('max_drawdown', 0):.2%}\n"
                message += f"🎯 胜率: {backtest_results.get('win_rate', 0):.2%}\n"
                message += f"🔄 交易次数: {backtest_results.get('trades_count', 0)}\n\n"
            
            # 时间戳
            message += f"⏰ *生成时间*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            return message
            
        except Exception as e:
            print(f"Error formatting signal message: {str(e)}")
            return f"Error formatting signal message: {str(e)}"
    
    def _format_html_signal(self, signal: Dict[str, Any], include_backtest: bool = True) -> str:
        """格式化 HTML 信号消息"""
        try:
            # 基本信息
            symbol = signal.get('symbol', 'Unknown')
            bias = signal.get('bias', 'NEUTRAL')
            signal_type = signal.get('signal_type', 'WEAK')
            signal_strength = signal.get('signal_strength', 0)
            suggested_strategy = signal.get('suggested_strategy', {})
            
            # 构建 HTML 消息
            color = "#22bb33" if bias == "BULLISH" else "#bb2124" if bias == "BEARISH" else "#f0ad4e"
            
            html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                <h2 style="color: {color}; text-align: center;">交易信号 - {symbol}</h2>
                <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 15px;">
                    <p><strong>方向:</strong> {bias}</p>
                    <p><strong>信号强度:</strong> {signal_strength:.2f}</p>
                    <p><strong>信号类型:</strong> {signal_type}</p>
                </div>
            """
            
            # 建议策略
            if suggested_strategy:
                strategy_type = suggested_strategy.get('type', 'Unknown')
                strike = suggested_strategy.get('strike', 0)
                expiration_days = suggested_strategy.get('expiration_days', 0)
                reason = suggested_strategy.get('reason', '')
                
                html += f"""
                <div style="background-color: #f0f7fb; padding: 15px; border-radius: 5px; margin-bottom: 15px;">
                    <h3 style="color: #2a6496; margin-top: 0;">建议策略</h3>
                    <p><strong>类型:</strong> {strategy_type}</p>
                    <p><strong>执行价:</strong> {strike}</p>
                    <p><strong>到期日:</strong> {expiration_days} 天</p>
                    <p><strong>理由:</strong> {reason}</p>
                </div>
                """
            
            # 逻辑链
            logic_chain = signal.get('logic_chain', [])
            if logic_chain:
                html += f"""
                <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 15px;">
                    <h3 style="color: #333; margin-top: 0;">分析逻辑</h3>
                    <ol>
                """
                
                for logic in logic_chain:
                    html += f"<li>{logic}</li>"
                
                html += """
                    </ol>
                </div>
                """
            
            # 风险因素
            risk_factors = signal.get('risk_factors', [])
            if risk_factors:
                html += f"""
                <div style="background-color: #fcf8e3; padding: 15px; border-radius: 5px; margin-bottom: 15px;">
                    <h3 style="color: #8a6d3b; margin-top: 0;">风险因素</h3>
                    <ul style="color: #8a6d3b;">
                """
                
                for risk in risk_factors:
                    html += f"<li>{risk}</li>"
                
                html += """
                    </ul>
                </div>
                """
            
            # 回测结果
            backtest_results = signal.get('backtest_results', {})
            if include_backtest and backtest_results:
                html += f"""
                <div style="background-color: #dff0d8; padding: 15px; border-radius: 5px; margin-bottom: 15px;">
                    <h3 style="color: #3c763d; margin-top: 0;">回测结果</h3>
                    <p><strong>总收益:</strong> {backtest_results.get('total_return', 0):.2%}</p>
                    <p><strong>年化收益:</strong> {backtest_results.get('annualized_return', 0):.2%}</p>
                    <p><strong>最大回撤:</strong> {backtest_results.get('max_drawdown', 0):.2%}</p>
                    <p><strong>胜率:</strong> {backtest_results.get('win_rate', 0):.2%}</p>
                    <p><strong>交易次数:</strong> {backtest_results.get('trades_count', 0)}</p>
                </div>
                """
            
            # 时间戳
            html += f"""
                <div style="text-align: center; color: #777; font-size: 12px; margin-top: 20px;">
                    生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
            """
            
            return html
            
        except Exception as e:
            print(f"Error formatting HTML signal message: {str(e)}")
            return f"<p>Error formatting signal message: {str(e)}</p>"
    
    def send_telegram(self, signal: Dict[str, Any], include_backtest: bool = True) -> bool:
        """发送消息到 Telegram"""
        if not self.telegram_enabled:
            print("Telegram notification is not enabled.")
            return False
        
        try:
            message = self._format_signal_message(signal, include_backtest)
            
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            print(f"Error sending Telegram message: {str(e)}")
            return False
    
    def send_email(self, signal: Dict[str, Any], include_backtest: bool = True) -> bool:
        """发送电子邮件通知"""
        if not self.email_enabled:
            print("Email notification is not enabled.")
            return False
        
        try:
            subject = f"交易信号 - {signal.get('symbol', 'Unknown')} - {signal.get('bias', 'NEUTRAL')}"
            text_content = self._format_signal_message(signal, include_backtest)
            html_content = self._format_html_signal(signal, include_backtest)
            
            # 创建多部分消息
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.email_sender
            message["To"] = self.email_receiver
            
            # 添加纯文本和 HTML 版本
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            
            message.attach(part1)
            message.attach(part2)
            
            # 发送电子邮件
            with smtplib.SMTP(self.email_smtp_server, self.email_smtp_port) as server:
                server.starttls()
                server.login(self.email_sender, self.email_password)
                server.sendmail(
                    self.email_sender, self.email_receiver, message.as_string()
                )
            
            return True
            
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
    
    def notify(self, signal: Dict[str, Any], channels: List[str] = None, include_backtest: bool = True) -> Dict[str, bool]:
        """发送通知到指定渠道"""
        if channels is None:
            channels = ["telegram", "email"] if self.telegram_enabled or self.email_enabled else []
        
        results = {}
        
        if "telegram" in channels and self.telegram_enabled:
            results["telegram"] = self.send_telegram(signal, include_backtest)
        
        if "email" in channels and self.email_enabled:
            results["email"] = self.send_email(signal, include_backtest)
        
        return results

if __name__ == "__main__":
    # 测试代码
    notification_service = NotificationService()
    
    # 示例信号
    test_signal = {
        "symbol": "AAPL",
        "bias": "BULLISH",
        "signal_type": "STRONG",
        "signal_strength": 0.85,
        "suggested_strategy": {
            "type": "CALL_SPREAD",
            "strike": 150,
            "expiration_days": 14,
            "reason": "技术指标显示上涨趋势强劲，建议买入看涨期权价差策略"
        },
        "logic_chain": [
            "RSI 处于上升趋势",
            "价格突破关键阻力位",
            "成交量放大"
        ],
        "risk_factors": [
            "市场整体波动性增加",
            "近期有财报发布"
        ],
        "backtest_results": {
            "total_return": 0.28,
            "annualized_return": 0.35,
            "max_drawdown": 0.12,
            "win_rate": 0.67,
            "trades_count": 24
        }
    }
    
    # 发送通知
    results = notification_service.notify(test_signal)
    print(f"Notification results: {json.dumps(results)}") 