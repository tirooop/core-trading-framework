"""
Telegram AI助手
提供基于Telegram的交互式AI助手功能
支持语音命令、自动播报和交易指令处理
"""

import os
import logging
import asyncio
import threading
from typing import Optional, Dict, Any, List, Union, Callable
from datetime import datetime
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# 导入自定义模块
from utils.notifier_dispatcher import notifier
from utils.ai_voice_summarizer import voice_summarizer

logger = logging.getLogger(__name__)

class TelegramAIAssistant:
    """Telegram AI助手"""
    
    def __init__(self, telegram_token: Optional[str] = None):
        """
        初始化Telegram AI助手
        
        Args:
            telegram_token: Telegram Bot Token，如果不提供则从环境变量读取
        """
        self.telegram_token = telegram_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        
        if not self.telegram_token:
            logger.warning("未设置TELEGRAM_BOT_TOKEN环境变量，Telegram助手功能将被禁用")
            self.enabled = False
            return
            
        self.enabled = True
        self.updater = Updater(token=self.telegram_token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        
        # 权限控制 - 允许使用机器人的用户ID列表
        self.authorized_users = set(
            int(user_id) for user_id in 
            os.environ.get("TELEGRAM_AUTHORIZED_USERS", "").split(",") 
            if user_id.strip().isdigit()
        )
        
        # 功能回调 - 可由外部模块注册
        self.command_handlers = {}
        
        # 设置命令处理器
        self._setup_handlers()
        
        logger.info("Telegram AI助手初始化完成")
    
    def _setup_handlers(self):
        """设置Telegram命令处理器"""
        # 基础命令
        self.dispatcher.add_handler(CommandHandler("start", self._start_command))
        self.dispatcher.add_handler(CommandHandler("help", self._help_command))
        self.dispatcher.add_handler(CommandHandler("status", self._status_command))
        
        # 语音功能
        self.dispatcher.add_handler(CommandHandler("voice", self._voice_command))
        self.dispatcher.add_handler(CommandHandler("dailyreport", self._daily_report_command))
        
        # 交易相关命令
        self.dispatcher.add_handler(CommandHandler("positions", self._positions_command))
        self.dispatcher.add_handler(CommandHandler("strategies", self._strategies_command))
        
        # 处理未知命令
        self.dispatcher.add_handler(MessageHandler(Filters.command, self._unknown_command))
        
        # 处理普通消息
        self.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, self._handle_message))
    
    def register_command_handler(self, command: str, handler: Callable):
        """
        注册外部命令处理器
        
        Args:
            command: 命令名称 (不含斜杠)
            handler: 处理函数，接收 Update 和 CallbackContext 参数
        """
        self.command_handlers[command] = handler
        logger.info(f"已注册外部命令处理器: {command}")
    
    def _is_authorized(self, user_id: int) -> bool:
        """检查用户是否有权限使用机器人"""
        # 如果未设置授权用户，则默认允许所有用户
        if not self.authorized_users:
            return True
        return user_id in self.authorized_users
    
    def _start_command(self, update: Update, context: CallbackContext):
        """处理/start命令"""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            update.message.reply_text("⛔ 您没有权限使用此机器人。")
            return
            
        update.message.reply_text(
            "🤖 *欢迎使用AI交易助手*\n\n"
            "我可以帮助您监控交易、生成报告和发送语音提醒。\n\n"
            "输入 /help 查看可用命令列表。",
            parse_mode="Markdown"
        )
    
    def _help_command(self, update: Update, context: CallbackContext):
        """处理/help命令"""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            return
            
        help_text = (
            "🤖 *AI交易助手命令列表*\n\n"
            "*基础命令*\n"
            "/start - 启动机器人\n"
            "/help - 显示帮助信息\n"
            "/status - 显示系统状态\n\n"
            
            "*语音功能*\n"
            "/voice <文本> - 将文本转为语音播报\n"
            "/dailyreport - 生成今日交易报告\n\n"
            
            "*交易信息*\n"
            "/positions - 查看当前持仓\n"
            "/strategies - 查看策略状态\n"
        )
        
        update.message.reply_text(help_text, parse_mode="Markdown")
    
    def _status_command(self, update: Update, context: CallbackContext):
        """处理/status命令"""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            return
            
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        status_text = (
            f"🖥️ *系统状态*\n\n"
            f"运行时间: {current_time}\n"
            f"系统状态: 正常运行\n"
            f"通知系统: 活跃\n"
            f"语音系统: 活跃\n"
        )
        
        update.message.reply_text(status_text, parse_mode="Markdown")
    
    def _voice_command(self, update: Update, context: CallbackContext):
        """处理/voice命令 - 生成语音消息"""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            return
        
        # 获取命令后的文本
        text = " ".join(context.args)
        if not text:
            update.message.reply_text("⚠️ 请提供要转为语音的文本。例如: /voice 当前策略表现良好")
            return
        
        update.message.reply_text("🔊 正在生成语音消息...")
        
        # 生成并发送语音
        result = voice_summarizer.generate_and_send_voice_summary(
            raw_text=text,
            summary_type="trading_day",
            caption="🎙️ 用户请求的语音消息",
            notification_level="INFO"
        )
        
        if not result.get("success", False):
            update.message.reply_text("❌ 语音生成失败，请稍后重试。")
    
    def _daily_report_command(self, update: Update, context: CallbackContext):
        """处理/dailyreport命令 - 生成每日交易报告"""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            return
        
        update.message.reply_text("📊 正在生成每日交易报告...")
        
        # 这里应该调用每日报告生成模块
        # 实际项目中应从数据源获取真实数据
        report_text = (
            "📈 *今日交易总结*\n\n"
            "总盈亏: +$1,240.56\n"
            "交易次数: 18\n"
            "胜率: 66.7%\n\n"
            "*表现最佳策略*\n"
            "- Mean Reversion: +$620.32\n"
            "- Gamma Scalping: +$520.10\n\n"
            "*表现欠佳策略*\n"
            "- Breakout V2: -$95.65\n\n"
            "*明日预测*\n"
            "市场模式: 震荡偏多\n"
            "波动率预期: 中等\n"
        )
        
        # 发送文本报告
        update.message.reply_text(report_text, parse_mode="Markdown")
        
        # 生成语音摘要
        voice_summarizer.generate_and_send_voice_summary(
            raw_text=report_text,
            summary_type="market_close",
            caption="📊 今日交易报告语音摘要",
            notification_level="DAILY"
        )
    
    def _positions_command(self, update: Update, context: CallbackContext):
        """处理/positions命令 - 显示当前持仓"""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            return
        
        # 这里应该从实际数据源获取持仓数据
        positions_text = (
            "📋 *当前持仓*\n\n"
            "*期权*\n"
            "- SPY 440 Call (6/30): 5张，+15.2%\n"
            "- QQQ 380 Put (6/23): 3张，-5.5%\n\n"
            "*股票*\n"
            "- AAPL: 100股，+2.1%\n"
            "- MSFT: 50股，+0.8%\n\n"
            "*总市值*: $28,450.75\n"
            "*未实现盈亏*: +$1,245.60"
        )
        
        update.message.reply_text(positions_text, parse_mode="Markdown")
    
    def _strategies_command(self, update: Update, context: CallbackContext):
        """处理/strategies命令 - 显示策略状态"""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            return
        
        # 这里应该从实际数据源获取策略数据
        strategies_text = (
            "⚙️ *策略状态*\n\n"
            "✅ *活跃策略*\n"
            "- Mean Reversion: 运行中，今日P&L +$340\n"
            "- Gamma Scalping: 运行中，今日P&L +$520\n"
            "- MACD Crossover: 运行中，今日P&L -$45\n\n"
            "❌ *暂停策略*\n"
            "- Breakout V2: 已暂停 (连续亏损)\n"
            "- Volatility Arbitrage: 待市场条件\n\n"
            "*总计*: 3个活跃，2个暂停"
        )
        
        update.message.reply_text(strategies_text, parse_mode="Markdown")
    
    def _unknown_command(self, update: Update, context: CallbackContext):
        """处理未知命令"""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            return
            
        command = update.message.text.split()[0]
        
        # 检查是否有注册的外部处理器
        command_name = command.lstrip('/')
        if command_name in self.command_handlers:
            # 调用外部处理器
            self.command_handlers[command_name](update, context)
            return
        
        update.message.reply_text(f"❓ 未知命令: {command}\n使用 /help 查看可用命令列表。")
    
    def _handle_message(self, update: Update, context: CallbackContext):
        """处理普通消息文本"""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            return
        
        # 简单回复，实际项目中可以接入更复杂的对话处理
        update.message.reply_text(
            "👋 您好！请使用命令与我交互。\n"
            "输入 /help 查看所有可用命令。"
        )
    
    def start(self):
        """启动Telegram机器人"""
        if not self.enabled:
            logger.warning("Telegram机器人未启用，请检查TOKEN设置")
            return
            
        logger.info("启动Telegram AI助手...")
        self.updater.start_polling()
        logger.info("Telegram AI助手已启动")
    
    def start_background(self):
        """在后台线程中启动Telegram机器人"""
        if not self.enabled:
            logger.warning("Telegram机器人未启用，请检查TOKEN设置")
            return None
            
        bot_thread = threading.Thread(target=self.start, daemon=True)
        bot_thread.start()
        logger.info("Telegram AI助手在后台线程中启动")
        return bot_thread
    
    def stop(self):
        """停止Telegram机器人"""
        if not self.enabled:
            return
            
        logger.info("正在停止Telegram AI助手...")
        self.updater.stop()
        logger.info("Telegram AI助手已停止")
    
    def send_message(self, chat_id: Union[str, int], text: str, parse_mode: Optional[str] = "Markdown") -> bool:
        """
        发送消息到指定聊天
        
        Args:
            chat_id: 目标聊天ID
            text: 消息文本
            parse_mode: 解析模式，默认为Markdown
            
        Returns:
            是否发送成功
        """
        if not self.enabled:
            logger.warning("Telegram机器人未启用，无法发送消息")
            return False
            
        try:
            self.updater.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
            return True
        except Exception as e:
            logger.error(f"发送Telegram消息失败: {str(e)}")
            return False

# 单例模式，方便直接导入使用
telegram_assistant = TelegramAIAssistant()

# 测试代码
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 启动Telegram机器人
    assistant = TelegramAIAssistant()
    assistant.start()
    
    try:
        # 保持程序运行
        while True:
            # 主循环
            pass
    except KeyboardInterrupt:
        # 优雅地停止机器人
        assistant.stop()
        print("Telegram AI助手已停止") 