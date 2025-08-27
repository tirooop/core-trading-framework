#!/usr/bin/env python


"""


AI Router - 多模型AI支持模块


支持: DeepSeek / OpenAI / Claude


自动选择可用模型并支持优先级路由


"""





import os


import json


import logging


import aiohttp


import asyncio


from typing import List, Dict, Optional, Union, Any





logger = logging.getLogger(__name__)





class AIRouter:


    """


    AI路由器 - 支持多AI引擎智能路由


    自动容错和降级功能


    """


    


    def __init__(self, config: Dict = None):


        """


        初始化AI路由器


        


        Args:


            config: 配置字典，包含各AI提供商的配置


        """


        self.config = config or {}


        self._load_config()


        self.providers = {


            "deepseek": self._call_deepseek,


            "openai": self._call_openai,


            "claude": self._call_claude


        }


        self.last_error = None


        


    def _load_config(self):


        """从配置文件加载AI配置"""


        try:


            if not self.config:


                # 尝试从warmachine_config.json加载配置


                config_path = os.path.join("config", "warmachine_config.json")


                if os.path.exists(config_path):


                    with open(config_path, "r", encoding="utf-8") as f:


                        self.config = json.load(f).get("ai", {})


                else:


                    config_path = os.path.join("config", "warmachine_community_config.json")


                    if os.path.exists(config_path):


                        with open(config_path, "r", encoding="utf-8") as f:


                            self.config = json.load(f).get("ai", {})


            


            # 设置默认值


            self.provider_priority = self.config.get("provider_priority", ["deepseek", "openai", "claude"])


            self.default_model = self.config.get("default_model", "deepseek-ai/DeepSeek-V3")


            self.temperature = self.config.get("temperature", 0.7)


            self.max_tokens = self.config.get("max_tokens", 4000)


            


            # API密钥


            self.deepseek_api_key = self.config.get("api_key", "")


            self.openai_api_key = self.config.get("fallback_api_key", "")


            self.claude_api_key = self.config.get("claude_api_key", "")


            


            # 基础URL


            self.deepseek_base_url = self.config.get("base_url", "https://api.siliconflow.cn/v1")


            self.openai_base_url = self.config.get("openai_base_url", "https://api.openai.com/v1")


            self.claude_base_url = self.config.get("claude_base_url", "https://api.anthropic.com/v1")


            


            # 模型映射


            self.model_mapping = {


                "deepseek": self.config.get("model", "deepseek-ai/DeepSeek-V3"),


                "openai": self.config.get("openai_model", "gpt-4-turbo"),


                "claude": self.config.get("claude_model", "claude-3-opus-20240229")


            }


            


            logger.info(f"AI路由器已初始化，优先级: {self.provider_priority}")


        except Exception as e:


            logger.error(f"加载AI配置失败: {e}")


            # 设置默认值


            self.provider_priority = ["deepseek", "openai", "claude"]


            self.default_model = "deepseek-ai/DeepSeek-V3"


            self.temperature = 0.7


            self.max_tokens = 4000


    


    async def ask(self, prompt: str, provider: str = None, system_prompt: str = None) -> str:


        """


        向AI发送请求并获取回答


        


        Args:


            prompt: 用户问题


            provider: 指定AI提供商，如不指定则按优先级自动选择


            system_prompt: 系统提示词


            


        Returns:


            AI回答文本


        """


        if provider and provider in self.providers:


            # 使用指定提供商


            try:


                response = await self.providers[provider](prompt, system_prompt)


                return response


            except Exception as e:


                self.last_error = str(e)


                logger.error(f"{provider} 请求失败: {e}")


                # 指定提供商失败，不进行降级处理


                return f"错误: {provider} 请求失败 - {str(e)}"


        else:


            # 按优先级顺序尝试


            for provider in self.provider_priority:


                if provider not in self.providers:


                    continue


                


                try:


                    response = await self.providers[provider](prompt, system_prompt)


                    return response


                except Exception as e:


                    self.last_error = str(e)


                    logger.error(f"{provider} 请求失败: {e}")


                    # 继续尝试下一个提供商


            


            # 所有提供商都失败


            return "错误: 所有AI提供商都请求失败"


    


    async def _call_deepseek(self, prompt: str, system_prompt: str = None) -> str:


        """调用DeepSeek API"""


        if not self.deepseek_api_key:


            raise ValueError("DeepSeek API密钥未设置")


        


        model = self.model_mapping.get("deepseek", self.default_model)


        system = system_prompt or "你是WarMachine，一个专业的AI量化交易分析师"


        


        headers = {


            "Content-Type": "application/json",


            "Authorization": f"Bearer {self.deepseek_api_key}"


        }


        


        payload = {


            "model": model,


            "messages": [


                {"role": "system", "content": system},


                {"role": "user", "content": prompt}


            ],


            "temperature": self.temperature,


            "max_tokens": self.max_tokens


        }


        


        async with aiohttp.ClientSession() as session:


            async with session.post(


                f"{self.deepseek_base_url}/chat/completions", 


                headers=headers, 


                json=payload


            ) as response:


                if response.status != 200:


                    error_text = await response.text()


                    raise Exception(f"DeepSeek API错误 ({response.status}): {error_text}")


                


                result = await response.json()


                return result["choices"][0]["message"]["content"]


    


    async def _call_openai(self, prompt: str, system_prompt: str = None) -> str:


        """调用OpenAI API"""


        if not self.openai_api_key:


            raise ValueError("OpenAI API密钥未设置")


        


        model = self.model_mapping.get("openai", "gpt-4-turbo")


        system = system_prompt or "你是WarMachine，一个专业的AI量化交易分析师"


        


        headers = {


            "Content-Type": "application/json",


            "Authorization": f"Bearer {self.openai_api_key}"


        }


        


        payload = {


            "model": model,


            "messages": [


                {"role": "system", "content": system},


                {"role": "user", "content": prompt}


            ],


            "temperature": self.temperature,


            "max_tokens": self.max_tokens


        }


        


        async with aiohttp.ClientSession() as session:


            async with session.post(


                f"{self.openai_base_url}/chat/completions", 


                headers=headers, 


                json=payload


            ) as response:


                if response.status != 200:


                    error_text = await response.text()


                    raise Exception(f"OpenAI API错误 ({response.status}): {error_text}")


                


                result = await response.json()


                return result["choices"][0]["message"]["content"]


    


    async def _call_claude(self, prompt: str, system_prompt: str = None) -> str:


        """调用Claude API"""


        if not self.claude_api_key:


            raise ValueError("Claude API密钥未设置")


        


        model = self.model_mapping.get("claude", "claude-3-opus-20240229")


        system = system_prompt or "你是WarMachine，一个专业的AI量化交易分析师"


        


        headers = {


            "Content-Type": "application/json",


            "x-api-key": f"{self.claude_api_key}",


            "anthropic-version": "2023-06-01"


        }


        


        payload = {


            "model": model,


            "messages": [


                {"role": "system", "content": system},


                {"role": "user", "content": prompt}


            ],


            "temperature": self.temperature,


            "max_tokens": self.max_tokens


        }


        


        async with aiohttp.ClientSession() as session:


            async with session.post(


                f"{self.claude_base_url}/messages", 


                headers=headers, 


                json=payload


            ) as response:


                if response.status != 200:


                    error_text = await response.text()


                    raise Exception(f"Claude API错误 ({response.status}): {error_text}")


                


                result = await response.json()


                return result["content"][0]["text"]





# 同步包装器


class AIRouterSync:


    """AIRouter的同步接口包装器"""


    


    def __init__(self, config: Dict = None):


        self.router = AIRouter(config)


        self.loop = asyncio.get_event_loop()


    


    def ask(self, prompt: str, provider: str = None, system_prompt: str = None) -> str:


        """同步调用AI"""


        return self.loop.run_until_complete(


            self.router.ask(prompt, provider, system_prompt)


        )





# 示例用法


async def example():


    router = AIRouter()


    response = await router.ask("分析AAPL最近的价格走势")


    print(response)


    


    # 指定使用OpenAI


    response = await router.ask("分析TSLA最近的价格走势", provider="openai")


    print(response)





# 直接运行测试


if __name__ == "__main__":


    logging.basicConfig(level=logging.INFO)


    asyncio.run(example()) 