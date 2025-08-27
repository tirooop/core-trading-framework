"""


AI语音摘要生成器


将AI生成的文本转换为语音并发送到Telegram


支持通知等级和格式约束


"""





import os


import requests


import tempfile


import logging


import asyncio


from pathlib import Path


from datetime import datetime


from typing import Optional, Dict, Any, Union, Literal


import telegram


from telegram import Bot


from dotenv import load_dotenv


# Import DeepSeek API functions


from utils.deepseek_api import get_deepseek_response





logger = logging.getLogger(__name__)





class AIVoiceSummarizer:


    """将AI文本摘要转换为语音并发送到Telegram，支持通知等级"""


    


    def __init__(self, telegram_token: Optional[str] = None, telegram_chat_id: Optional[str] = None):


        """


        初始化AI语音摘要器


        


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


            


        # DeepSeek API Key


        self.api_key = os.environ.get("DEEPSEEK_API_KEY")


        


        # Edge TTS base URL (Microsoft Edge TTS is free and high quality)


        self.edge_tts_url = "https://api.edge-tts.com/v1/speak"


        


        # Create temp directory for audio files if it doesn't exist


        self.temp_dir = Path("temp_audio")


        self.temp_dir.mkdir(exist_ok=True)


        


        # 通知等级对应的语音风格


        self.voice_styles = {


            "INFO": {"voice": "zh-CN-XiaoxiaoNeural", "rate": "0", "pitch": "0"},


            "WARN": {"voice": "zh-CN-YunxiNeural", "rate": "+10%", "pitch": "0"},


            "ALERT": {"voice": "zh-CN-YunjianNeural", "rate": "+20%", "pitch": "+10%"},


            "DAILY": {"voice": "zh-CN-YunyangNeural", "rate": "0", "pitch": "0"}


        }


    


    def generate_summary(self, 


                        raw_text: str, 


                        summary_type: str = "trading_day",


                        max_tokens: int = 150,


                        notification_level: str = "INFO") -> str:


        """


        使用DeepSeek生成文本摘要，限制字数提高效率


        


        Args:


            raw_text: 原始文本内容


            summary_type: 摘要类型 (trading_day, market_open, market_close, options_alert)


            max_tokens: 生成的最大token数量


            notification_level: 通知等级 (INFO, WARN, ALERT, DAILY)


            


        Returns:


            生成的摘要文本


        """


        # 根据摘要类型选择系统提示


        system_prompts = {


            "trading_day": "You are a seasoned trader's AI assistant. Provide a brief trading summary, limited to 50 characters. Directly give the key points, without explanation, and avoid using complex terminology. ",


            "market_open": "You are a trader's AI assistant. Provide a brief summary before the market opens, limited to 40 characters. Directly give the key points, without explanation. ",


            "market_close": "You are a seasoned trader's AI assistant. Provide a brief summary after the market closes, limited to 50 characters. Highlight key data, avoid detailed analysis. ",


            "options_alert": "You are an options trading expert. Provide an urgent brief reminder, limited to 30 characters. Directly state the situation and action suggestions. "


        }


        


        system_prompt = system_prompts.get(summary_type, system_prompts["trading_day"])


        


        # 根据通知等级调整提示风格


        level_prompt_addons = {


            "INFO": "Use a calm, informational tone.",


            "WARN": "Use a cautious reminder tone, but don't over-stress.",


            "ALERT": "Use an urgent warning tone, emphasizing the need to pay attention immediately.",


            "DAILY": "Use a summary tone, emphasizing the overall performance of the day."


        }


        


        system_prompt += level_prompt_addons.get(notification_level, "")


        


        # 简化提示，减少字数限制，提高API效率


        prompt = f"""


Please convert the following trading/market information into a concise voice summary, limited to {max_tokens//2} characters:





{raw_text}





Requirements:


1. Directly give key information, without an introduction


2. Use short phrases


3. Only highlight the most important data points


4. Suitable for voice announcement


"""


        


        try:


            summary = get_deepseek_response(


                prompt=prompt,


                api_key=self.api_key,


                max_tokens=max_tokens,


                temperature=0.3,  # 降低温度以获得更确定的回答


                system_prompt=system_prompt


            )


            


            logger.debug(f"Successfully generated summary: {summary[:50]}...")


            return summary


        except Exception as e:


            error_msg = f"Error generating summary: {str(e)}"


            logger.error(error_msg)


            return f"Summary generation failed: {error_msg}"





    async def text_to_speech_edge_async(self, 


                                text: str, 


                                output_file: Optional[str] = None,


                                notification_level: str = "INFO") -> str:


        """


        使用Microsoft Edge TTS将文本转换为语音（异步版本）


        


        Args:


            text: 要转换的文本


            output_file: 输出文件路径，如果不提供则创建临时文件


            notification_level: 通知等级，决定语音风格


            


        Returns:


            生成的音频文件路径


        """


        import edge_tts


        


        if not output_file:


            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


            output_file = str(self.temp_dir / f"voice_{notification_level}_{timestamp}.mp3")


        


        try:


            # 获取对应等级的语音风格


            voice_style = self.voice_styles.get(notification_level, self.voice_styles["INFO"])


            voice_name = voice_style["voice"]


            


            # 创建edge_tts的Communicate实例


            communicate = edge_tts.Communicate(text, voice_name)


            


            # 保存到文件


            await communicate.save(output_file)


            


            logger.debug(f"Successfully generated voice file: {output_file}")


            return output_file


        except Exception as e:


            logger.error(f"Error generating voice: {str(e)}")


            return ""





    def text_to_speech_edge(self, 


                          text: str, 


                          output_file: Optional[str] = None,


                          notification_level: str = "INFO") -> str:


        """


        使用Microsoft Edge TTS将文本转换为语音（同步版本）


        


        Args:


            text: 要转换的文本


            output_file: 输出文件路径，如果不提供则创建临时文件


            notification_level: 通知等级，决定语音风格


            


        Returns:


            生成的音频文件路径


        """


        return asyncio.run(self.text_to_speech_edge_async(text, output_file, notification_level))


    


    def send_voice_to_telegram(self, 


                             file_path: str, 


                             caption: Optional[str] = None,


                             notification_level: str = "INFO") -> bool:


        """


        发送语音文件到Telegram


        


        Args:


            file_path: 语音文件路径


            caption: 可选的语音消息说明文字


            notification_level: 通知等级


            


        Returns:


            是否发送成功


        """


        if not self.telegram_token or not self.telegram_chat_id:


            logger.warning("未设置Telegram配置，语音消息发送失败")


            return False


        


        try:


            bot = Bot(token=self.telegram_token)


            


            # 如果没有提供说明，则根据等级生成默认说明


            if not caption:


                level_captions = {


                    "INFO": "🔊 Trading Information Voice Announcement",


                    "WARN": "⚠️ Trading Warning Voice Announcement",


                    "ALERT": "�� Trading Urgent Reminder",


                    "DAILY": "📊 Daily Trading Summary"


                }


                caption = level_captions.get(notification_level, "🔊 Voice Announcement")


            


            with open(file_path, 'rb') as audio:


                bot.send_voice(chat_id=self.telegram_chat_id, voice=audio, caption=caption)


            


            logger.info(f"Successfully sent voice message to Telegram: {file_path}")


            return True


        except Exception as e:


            logger.error(f"Error sending to Telegram: {str(e)}")


            return False


    


    def generate_and_send_voice_summary(self, 


                                      raw_text: str, 


                                      summary_type: str = "trading_day", 


                                      caption: Optional[str] = None,


                                      notification_level: str = "INFO",


                                      max_tokens: int = 150) -> Dict[str, Any]:


        """


        生成摘要并发送语音到Telegram (一体化流程)


        


        Args:


            raw_text: 原始文本内容


            summary_type: 摘要类型


            caption: 可选的语音消息说明文字


            notification_level: 通知等级 (INFO, WARN, ALERT, DAILY)


            max_tokens: 生成的最大token数量


            


        Returns:


            Dict with status and results


        """


        try:


            # 生成文本摘要


            summary = self.generate_summary(


                raw_text, 


                summary_type, 


                max_tokens=max_tokens,


                notification_level=notification_level


            )


            


            # 转换为语音


            voice_file = self.text_to_speech_edge(


                summary, 


                notification_level=notification_level


            )


            


            if not voice_file:


                return {


                    "success": False,


                    "error": "语音生成失败",


                    "summary": summary


                }


            


            # 根据通知等级添加前缀


            level_icons = {


                "INFO": "🔊",


                "WARN": "⚠️",


                "ALERT": "🚨",


                "DAILY": "📊"


            }


            icon = level_icons.get(notification_level, "🔊")


            


            # 发送到Telegram


            custom_caption = caption or f"{icon} {summary_type.replace('_', ' ').title()} Voice Summary"


            sent = self.send_voice_to_telegram(


                voice_file, 


                custom_caption,


                notification_level


            )


            


            # 清理临时文件


            try:


                if os.path.exists(voice_file):


                    os.remove(voice_file)


            except OSError:


                pass


            


            return {


                "success": sent,


                "summary": summary,


                "notification_level": notification_level,


                "file_path": voice_file if sent else None


            }


        except Exception as e:


            logger.error(f"Error generating and sending voice summary: {str(e)}")


            return {


                "success": False,


                "error": str(e)


            }





# 单例模式，方便直接导入使用


voice_summarizer = AIVoiceSummarizer()





# 测试代码


if __name__ == "__main__":


    # 测试不同级别的语音摘要生成和发送


    test_text = """


    今日SPY表现:


    - 开盘价: $432.15


    - 收盘价: $436.78 (+1.07%)


    - 成交量: 87.3M (高于20日均值)


    


    策略表现:


    1. Mean Reversion: +$340


    2. Gamma Scalping: +$520


    3. Breakout V2: -$120


    


    总盈亏: +$740


    当前持仓:


    - SPY 430 Call: 5张 (+10%)


    - AAPL: 100股 (-0.5%)


    


    市场情绪:


    - VIX: 14.3 (-5%)


    - 净多单: 增加


    """


    


    # 测试普通信息播报


    info_result = voice_summarizer.generate_and_send_voice_summary(


        test_text, 


        summary_type="market_close",


        caption="📊 今日收盘语音摘要",


        notification_level="INFO"


    )


    


    print(f"INFO发送结果: {'成功' if info_result['success'] else '失败'}")


    print(f"INFO生成的摘要:\n{info_result['summary']}")


    


    # 测试警告级别播报


    warn_text = "策略Breakout V2连续3次交易亏损，总亏损超过200美元，请注意风险控制。"


    warn_result = voice_summarizer.generate_and_send_voice_summary(


        warn_text,


        summary_type="trading_day",


        caption="⚠️ 策略风险提醒",


        notification_level="WARN"


    )


    


    print(f"WARN发送结果: {'成功' if warn_result['success'] else '失败'}")


    print(f"WARN生成的摘要:\n{warn_result['summary']}")


    


    # 测试警报级别播报


    alert_text = "组合风险值突破预警线，当前回撤已达8.5%，多个策略停止运行，请立即检查。"


    alert_result = voice_summarizer.generate_and_send_voice_summary(


        alert_text,


        summary_type="options_alert",


        caption="🚨 紧急风险警报",


        notification_level="ALERT",


        max_tokens=100  # 紧急消息更简短


    )


    


    print(f"ALERT发送结果: {'成功' if alert_result['success'] else '失败'}")


    print(f"ALERT生成的摘要:\n{alert_result['summary']}") 