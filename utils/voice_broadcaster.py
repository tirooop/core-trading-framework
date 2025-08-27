#!/usr/bin/env python


"""


Voice broadcasting module - Supports Telegram and Discord voice file generation and sending


Provides AI text-to-speech functionality and automatic broadcasting


"""





import os


import sys


import json


import logging


import asyncio


import tempfile


import datetime


import random


from typing import Dict, List, Optional, Any, Union





# 导入相关模块


try:


    import edge_tts


except ImportError:


    print("Warning: edge_tts not installed, some voice features will be unavailable")


    print("Please run: pip install edge-tts")





logger = logging.getLogger(__name__)





class VoiceBroadcaster:


    """


    Voice broadcasting module


    Supports Telegram and Discord group voice push


    """


    


    def __init__(self, config: Dict = None, telegram_bot = None, discord_bot = None):


        """


        Initialize voice broadcaster


        


        Args:


            config: Configuration dictionary


            telegram_bot: Telegram bot instance


            discord_bot: Discord bot instance


        """


        self.config = config or {}


        self._load_config()


        


        # Message notifiers


        self.telegram_bot = telegram_bot


        self.discord_bot = discord_bot


        


        # Temporary directory


        self.temp_dir = os.path.join("data", "temp_audio")


        os.makedirs(self.temp_dir, exist_ok=True)


        


        logger.info("Voice broadcasting module initialized")


    


    def _load_config(self):


        """从配置文件加载配置"""


        try:


            if not self.config:


                # 尝试加载社区版配置


                config_path = os.path.join("config", "warmachine_community_config.json")


                if os.path.exists(config_path):


                    with open(config_path, "r", encoding="utf-8") as f:


                        config = json.load(f)


                        self.config = config.get("voice_broadcaster", {})


                else:


                    # 尝试从普通配置加载


                    config_path = os.path.join("config", "warmachine_config.json")


                    if os.path.exists(config_path):


                        with open(config_path, "r", encoding="utf-8") as f:


                            config = json.load(f)


                            self.config = config.get("voice_broadcaster", {})


            


            # 设置默认值


            self.enabled = self.config.get("enabled", True)


            


            # TTS engine settings


            self.tts_engine = self.config.get("tts_engine", "edge-tts")


            


            # Voice settings


            self.voice_settings = self.config.get("voice_settings", {


                "default": {


                    "voice": "zh-CN-XiaoxiaoNeural",


                    "rate": "+0%",


                    "volume": "+0%"


                },


                "market": {


                    "voice": "zh-CN-YunxiNeural",


                    "rate": "+10%",


                    "volume": "+0%"


                },


                "alert": {


                    "voice": "zh-CN-YunyangNeural",


                    "rate": "+15%",


                    "volume": "+10%"


                }


            })


            


            # Channel settings


            self.telegram_channels = self.config.get("telegram_channels", [])


            self.discord_voice_channels = self.config.get("discord_voice_channels", [])


            


            # Cleanup settings


            self.cleanup_interval = self.config.get("cleanup_interval", 86400)  # One day


            self.max_age = self.config.get("max_age", 604800)  # One week


            


            logger.info(f"语音广播模块配置加载完成，TTS引擎: {self.tts_engine}")


        except Exception as e:


            logger.error(f"加载语音广播模块配置失败: {e}")


            # 设置默认值


            self.enabled = True


            self.tts_engine = "edge-tts"


            self.voice_settings = {


                "default": {


                    "voice": "zh-CN-XiaoxiaoNeural",


                    "rate": "+0%",


                    "volume": "+0%"


                }


            }


            self.telegram_channels = []


            self.discord_voice_channels = []


            self.cleanup_interval = 86400


            self.max_age = 604800


    


    async def text_to_speech(self, text: str, voice_type: str = "default") -> Optional[str]:


        """


        文本转语音


        


        Args:


            text: 要转换为语音的文本


            voice_type: 语音类型，default/market/alert等


            


        Returns:


            生成的语音文件路径，若失败则返回None


        """


        if not self.enabled:


            logger.warning("语音广播模块已禁用")


            return None


            


        try:


            # 获取语音设置


            voice_config = self.voice_settings.get(voice_type, self.voice_settings["default"])


            voice = voice_config.get("voice", "zh-CN-XiaoxiaoNeural")


            rate = voice_config.get("rate", "+0%")


            volume = voice_config.get("volume", "+0%")


            


            # 文件命名


            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


            file_path = os.path.join(self.temp_dir, f"voice_{timestamp}_{random.randint(1000, 9999)}.mp3")


            


            if self.tts_engine == "edge-tts":


                return await self._edge_tts(text, file_path, voice, rate, volume)


                


            else:


                logger.error(f"不支持的TTS引擎: {self.tts_engine}")


                return None


        except Exception as e:


            logger.error(f"生成语音失败: {e}")


            return None


    


    async def _edge_tts(self, text: str, file_path: str, voice: str, rate: str, volume: str) -> Optional[str]:


        """


        使用Edge TTS生成语音


        


        Args:


            text: 文本


            file_path: 输出文件路径


            voice: 语音名称


            rate: 语速


            volume: 音量


            


        Returns:


            生成的语音文件路径


        """


        try:


            # 检查edge_tts是否已安装


            if "edge_tts" not in sys.modules:


                logger.error("Edge TTS未安装")


                return None


                


            communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)


            await communicate.save(file_path)


            


            logger.info(f"生成语音文件: {file_path}")


            return file_path


        except Exception as e:


            logger.error(f"Edge TTS生成语音失败: {e}")


            return None


    


    async def broadcast_voice_to_telegram(self, file_path: str, chat_ids: List[str] = None) -> bool:


        """


        向Telegram发送语音消息


        


        Args:


            file_path: 语音文件路径


            chat_ids: 聊天ID列表，若为None则使用配置中的默认频道


            


        Returns:


            是否全部发送成功


        """


        if not self.enabled or not self.telegram_bot:


            logger.warning("语音广播模块已禁用或Telegram机器人未配置")


            return False


            


        if not os.path.exists(file_path):


            logger.error(f"语音文件不存在: {file_path}")


            return False


            


        # 使用提供的chat_ids或默认频道


        targets = chat_ids or self.telegram_channels


        if not targets:


            logger.warning("没有Telegram目标频道")


            return False


            


        success = True


        


        try:


            # 调用Telegram机器人发送语音消息


            for chat_id in targets:


                try:


                    # 异步发送语音消息


                    # 这部分代码需要根据实际的Telegram机器人实现调整


                    await self.telegram_bot.send_voice(chat_id, file_path)


                    logger.info(f"已发送语音消息到Telegram: {chat_id}")


                except Exception as e:


                    logger.error(f"发送语音消息到Telegram {chat_id} 失败: {e}")


                    success = False


            


            return success


        except Exception as e:


            logger.error(f"向Telegram广播语音失败: {e}")


            return False


    


    async def broadcast_voice_to_discord(self, file_path: str, channel_ids: List[str] = None) -> bool:


        """


        向Discord发送语音消息


        


        Args:


            file_path: 语音文件路径


            channel_ids: 频道ID列表，若为None则使用配置中的默认频道


            


        Returns:


            是否全部发送成功


        """


        if not self.enabled or not self.discord_bot:


            logger.warning("语音广播模块已禁用或Discord机器人未配置")


            return False


            


        if not os.path.exists(file_path):


            logger.error(f"语音文件不存在: {file_path}")


            return False


            


        # 使用提供的channel_ids或默认频道


        targets = channel_ids or self.discord_voice_channels


        if not targets:


            logger.warning("没有Discord目标频道")


            return False


            


        success = True


        


        try:


            # 调用Discord机器人发送语音消息


            for channel_id in targets:


                try:


                    # 异步发送语音消息


                    # 这部分代码需要根据实际的Discord机器人实现调整


                    await self.discord_bot.send_voice(channel_id, file_path)


                    logger.info(f"已发送语音消息到Discord: {channel_id}")


                except Exception as e:


                    logger.error(f"发送语音消息到Discord {channel_id} 失败: {e}")


                    success = False


            


            return success


        except Exception as e:


            logger.error(f"向Discord广播语音失败: {e}")


            return False


    


    async def broadcast_to_all(self, text: str, voice_type: str = "default") -> Dict[str, Any]:


        """


        向所有平台广播语音


        


        Args:


            text: 文本内容


            voice_type: 语音类型


            


        Returns:


            包含结果信息的字典


        """


        if not self.enabled:


            return {"success": False, "reason": "语音广播模块已禁用"}


            


        try:


            # 生成语音文件


            file_path = await self.text_to_speech(text, voice_type)


            if not file_path:


                return {"success": False, "reason": "生成语音文件失败"}


                


            results = {


                "success": True,


                "file_path": file_path,


                "telegram": False,


                "discord": False


            }


            


            # 向Telegram广播


            if self.telegram_bot and self.telegram_channels:


                results["telegram"] = await self.broadcast_voice_to_telegram(file_path)


                


            # 向Discord广播


            if self.discord_bot and self.discord_voice_channels:


                results["discord"] = await self.broadcast_voice_to_discord(file_path)


                


            return results


        except Exception as e:


            logger.error(f"向所有平台广播语音失败: {e}")


            return {"success": False, "reason": str(e)}


    


    async def quick_broadcast(self, text: str, voice_type: str = "default") -> bool:


        """


        快速向所有平台广播语音，简化版接口


        


        Args:


            text: 文本内容


            voice_type: 语音类型


            


        Returns:


            是否成功


        """


        result = await self.broadcast_to_all(text, voice_type)


        return result.get("success", False)


    


    def cleanup_old_files(self):


        """清理过期的语音文件"""


        try:


            now = datetime.datetime.now()


            count = 0


            


            for filename in os.listdir(self.temp_dir):


                file_path = os.path.join(self.temp_dir, filename)


                # 检查是否为文件且后缀为.mp3


                if os.path.isfile(file_path) and filename.endswith(".mp3"):


                    # 获取文件修改时间


                    mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))


                    # 计算文件年龄（秒）


                    age = (now - mod_time).total_seconds()


                    


                    # 如果文件超过最大年龄，则删除


                    if age > self.max_age:


                        os.remove(file_path)


                        count += 1


                        


            logger.info(f"清理了 {count} 个过期语音文件")


        except Exception as e:


            logger.error(f"清理语音文件失败: {e}")





# 同步包装器


class VoiceBroadcasterSync:


    """VoiceBroadcaster的同步接口包装器"""


    


    def __init__(self, config: Dict = None, telegram_bot = None, discord_bot = None):


        self.broadcaster = VoiceBroadcaster(config, telegram_bot, discord_bot)


        self.loop = asyncio.get_event_loop()


    


    def text_to_speech(self, text: str, voice_type: str = "default") -> Optional[str]:


        """同步调用text_to_speech"""


        return self.loop.run_until_complete(


            self.broadcaster.text_to_speech(text, voice_type)


        )


    


    def broadcast_voice_to_telegram(self, file_path: str, chat_ids: List[str] = None) -> bool:


        """同步调用broadcast_voice_to_telegram"""


        return self.loop.run_until_complete(


            self.broadcaster.broadcast_voice_to_telegram(file_path, chat_ids)


        )


    


    def broadcast_voice_to_discord(self, file_path: str, channel_ids: List[str] = None) -> bool:


        """同步调用broadcast_voice_to_discord"""


        return self.loop.run_until_complete(


            self.broadcaster.broadcast_voice_to_discord(file_path, channel_ids)


        )


    


    def broadcast_to_all(self, text: str, voice_type: str = "default") -> Dict[str, Any]:


        """同步调用broadcast_to_all"""


        return self.loop.run_until_complete(


            self.broadcaster.broadcast_to_all(text, voice_type)


        )


    


    def quick_broadcast(self, text: str, voice_type: str = "default") -> bool:


        """同步调用quick_broadcast"""


        return self.loop.run_until_complete(


            self.broadcaster.quick_broadcast(text, voice_type)


        )


    


    def cleanup_old_files(self):


        """同步调用cleanup_old_files"""


        self.broadcaster.cleanup_old_files()





# 示例用法


async def example():


    # 模拟的消息发送器


    class MockTelegramBot:


        async def send_voice(self, chat_id, file_path):


            print(f"模拟发送语音到Telegram: {chat_id}, 文件: {file_path}")


    


    class MockDiscordBot:


        async def send_voice(self, channel_id, file_path):


            print(f"模拟发送语音到Discord: {channel_id}, 文件: {file_path}")


    


    # 测试配置


    config = {


        "enabled": True,


        "tts_engine": "edge-tts",


        "voice_settings": {


            "default": {


                "voice": "zh-CN-XiaoxiaoNeural",


                "rate": "+0%",


                "volume": "+0%"


            }


        },


        "telegram_channels": ["12345678"],


        "discord_voice_channels": ["87654321"]


    }


    


    # 创建广播器


    broadcaster = VoiceBroadcaster(


        config, 


        telegram_bot=MockTelegramBot(), 


        discord_bot=MockDiscordBot()


    )


    


    # 生成并广播语音


    file_path = await broadcaster.text_to_speech("这是一个测试消息")


    if file_path:


        print(f"生成语音文件: {file_path}")


        


        # 广播到Telegram


        await broadcaster.broadcast_voice_to_telegram(file_path)


        


        # 广播到Discord


        await broadcaster.broadcast_voice_to_discord(file_path)


        


        # 快速广播到所有平台


        await broadcaster.quick_broadcast("这是一条广播到所有平台的消息")





# 直接运行测试


if __name__ == "__main__":


    logging.basicConfig(level=logging.INFO)


    asyncio.run(example()) 