"""
通知分发器
支持多模态通知（文字、图片、语音）及通知优先级
集成Telegram和其他通知渠道
"""

import os
import logging
from typing import Optional, Dict, Any, List, Union, Literal
from pathlib import Path
import json
import telegram
from telegram import Bot
from PIL import Image

# 导入自定义模块
from utils.ai_voice_summarizer import voice_summarizer

logger = logging.getLogger(__name__)

# 通知级别类型
NotificationLevel = Literal["INFO", "WARN", "ALERT", "DAILY"]

# Helper function to check image format using PIL
def get_image_format(path):
    """
    使用PIL检查图片格式
    
    Args:
        path: 图片路径
        
    Returns:
        图片格式，如果不是有效图片则返回None
    """
    try:
        with Image.open(path) as img:
            return img.format
    except Exception as e:
        logger.error(f"检查图片格式时出错: {str(e)}")
        return None

class NotifierDispatcher:
    """多模态通知分发器"""
    
    def __init__(self, telegram_token: Optional[str] = None, telegram_chat_id: Optional[str] = None):
        """
        初始化通知分发器
        
        Args:
            telegram_token: Telegram Bot Token，如果不提供则从环境变量读取
            telegram_chat_id: Telegram Chat ID，如果不提供则从环境变量读取
        """
        self.telegram_token = telegram_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = telegram_chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        
        if not self.telegram_token:
            logger.warning("未设置TELEGRAM_BOT_TOKEN环境变量，Telegram推送功能将被禁用")
        
        if not self.telegram_chat_id:
            logger.warning("未设置TELEGRAM_CHAT_ID环境变量，Telegram推送功能将被禁用")
        
        # 语音摘要模块
        self.voice_summarizer = voice_summarizer
        
        # 通知级别对应的图标
        self.level_icons = {
            "INFO": "ℹ️",
            "WARN": "⚠️",
            "ALERT": "🚨",
            "DAILY": "📊"
        }
        
        # 通知历史记录
        self.notification_history = []
        self.max_history_size = 100
    
    def _format_message_with_level(self, message: str, level: NotificationLevel) -> str:
        """
        根据通知级别格式化消息
        
        Args:
            message: 原始消息
            level: 通知级别
            
        Returns:
            格式化后的消息
        """
        icon = self.level_icons.get(level, "ℹ️")
        return f"{icon} [{level}] {message}"
    
    def send_text(self, 
                 message: str, 
                 level: NotificationLevel = "INFO",
                 markdown: bool = True) -> bool:
        """
        发送文本消息到Telegram
        
        Args:
            message: 消息内容
            level: 通知级别 (INFO, WARN, ALERT, DAILY)
            markdown: 是否启用Markdown格式
            
        Returns:
            是否发送成功
        """
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("未设置Telegram配置，文本消息发送失败")
            return False
        
        try:
            bot = Bot(token=self.telegram_token)
            
            # 格式化消息
            formatted_message = self._format_message_with_level(message, level)
            
            # 记录到历史
            self._add_to_history({
                "type": "text",
                "level": level,
                "content": message
            })
            
            # 发送消息
            bot.send_message(
                chat_id=self.telegram_chat_id,
                text=formatted_message,
                parse_mode="Markdown" if markdown else None
            )
            
            logger.info(f"成功发送{level}级别文本消息到Telegram")
            return True
        except Exception as e:
            logger.error(f"发送文本消息到Telegram时出错: {str(e)}")
            return False
    
    def send_image(self, 
                  image_path: str, 
                  caption: Optional[str] = None,
                  level: NotificationLevel = "INFO") -> bool:
        """
        发送图片到Telegram
        
        Args:
            image_path: 图片文件路径
            caption: 图片说明
            level: 通知级别
            
        Returns:
            是否发送成功
        """
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("未设置Telegram配置，图片消息发送失败")
            return False
        
        try:
            # 检查图片格式
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return False
                
            # Use PIL to verify image
            image_format = get_image_format(image_path)
            if not image_format or image_format not in ["JPEG", "PNG", "GIF", "BMP"]:
                logger.error(f"不支持的图片格式或无效图片: {image_path}")
                return False
            
            bot = Bot(token=self.telegram_token)
            
            # 如果提供了说明，添加级别前缀
            if caption:
                formatted_caption = self._format_message_with_level(caption, level)
            else:
                icon = self.level_icons.get(level, "ℹ️")
                formatted_caption = f"{icon} 图表"
            
            # 记录到历史
            self._add_to_history({
                "type": "image",
                "level": level,
                "content": image_path,
                "caption": caption
            })
            
            # 发送图片
            with open(image_path, 'rb') as image_file:
                bot.send_photo(
                    chat_id=self.telegram_chat_id, 
                    photo=image_file, 
                    caption=formatted_caption
                )
            
            logger.info(f"成功发送{level}级别图片到Telegram: {image_path}")
            return True
        except Exception as e:
            logger.error(f"发送图片到Telegram时出错: {str(e)}")
            return False
    
    def send_voice(self, 
                  text: str, 
                  level: NotificationLevel = "INFO",
                  summary_type: str = "trading_day",
                  caption: Optional[str] = None) -> Dict[str, Any]:
        """
        发送AI生成的语音消息
        
        Args:
            text: 要转为语音的文本
            level: 通知级别
            summary_type: 摘要类型
            caption: 可选的消息说明
            
        Returns:
            操作结果字典
        """
        try:
            # 使用AI语音摘要器生成并发送语音
            result = self.voice_summarizer.generate_and_send_voice_summary(
                raw_text=text,
                summary_type=summary_type,
                caption=caption,
                notification_level=level
            )
            
            # 记录到历史
            if result.get("success", False):
                self._add_to_history({
                    "type": "voice",
                    "level": level,
                    "content": result.get("summary", ""),
                    "caption": caption
                })
            
            return result
        except Exception as e:
            logger.error(f"发送语音消息时出错: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def notify(self, 
              message: str, 
              level: NotificationLevel = "INFO", 
              image_path: Optional[str] = None, 
              voice: bool = False,
              summary_type: str = "trading_day") -> Dict[str, Any]:
        """
        综合通知函数（支持文本+图片+语音）
        
        Args:
            message: 消息内容
            level: 通知级别
            image_path: 可选的图片路径
            voice: 是否同时发送语音
            summary_type: 语音摘要类型
            
        Returns:
            操作结果字典
        """
        results = {}
        
        # 发送文本消息
        text_result = self.send_text(message, level)
        results["text"] = text_result
        
        # 如果提供了图片，发送图片
        if image_path:
            image_result = self.send_image(image_path, message, level)
            results["image"] = image_result
        
        # 如果需要语音，发送语音
        if voice:
            voice_result = self.send_voice(message, level, summary_type)
            results["voice"] = voice_result.get("success", False)
        
        # 返回综合结果
        results["success"] = text_result and (not image_path or results.get("image", True)) and (not voice or results.get("voice", True))
        
        return results
    
    def _add_to_history(self, notification: Dict[str, Any]):
        """添加通知到历史记录"""
        # 添加时间戳
        import datetime
        notification["timestamp"] = datetime.datetime.now().isoformat()
        
        # 添加到历史
        self.notification_history.append(notification)
        
        # 保持历史记录在最大大小以内
        if len(self.notification_history) > self.max_history_size:
            self.notification_history = self.notification_history[-self.max_history_size:]
    
    def get_history(self, 
                  level: Optional[NotificationLevel] = None, 
                  limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取通知历史
        
        Args:
            level: 可选的通知级别过滤
            limit: 返回的最大记录数
            
        Returns:
            通知历史列表
        """
        if level:
            filtered_history = [n for n in self.notification_history if n.get("level") == level]
        else:
            filtered_history = self.notification_history
        
        # 返回最近的n条记录
        return filtered_history[-limit:]

# 单例模式，方便直接导入使用
notifier = NotifierDispatcher()

# 测试代码
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 测试文本消息
    notifier.send_text("这是一条普通的信息通知", level="INFO")
    notifier.send_text("这是一条警告通知，需要注意", level="WARN")
    notifier.send_text("这是一条紧急警报，需要立即处理！", level="ALERT")
    
    # 测试语音消息
    notifier.send_voice(
        "策略Mean Reversion今日表现良好，盈利320美元，总回撤控制在2%以内。",
        level="INFO",
        summary_type="trading_day"
    )
    
    # 测试综合通知
    notifier.notify(
        "组合回撤超过5%，请注意风险",
        level="WARN",
        voice=True,
        summary_type="options_alert"
    ) 