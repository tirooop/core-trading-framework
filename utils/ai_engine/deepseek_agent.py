"""


DeepSeek AI 代理





提供与DeepSeek API的统一交互接口，为AI量化社区平台提供核心AI能力。


支持文本生成、策略生成、图表分析等功能。


"""





import os


import json


import logging


import requests


import time


import re


from typing import Dict, List, Any, Optional, Union, Tuple





logger = logging.getLogger(__name__)





class DeepSeekAgent:


    """DeepSeek AI代理"""


    


    def __init__(self, 


                 api_key: Optional[str] = None, 


                 model: str = "deepseek-ai/DeepSeek-V3",


                 base_url: str = "https://api.siliconflow.cn/v1",


                 max_retries: int = 3,


                 retry_delay: int = 2):


        """


        初始化DeepSeek AI代理


        


        Args:


            api_key: DeepSeek API密钥，为None时从环境变量获取


            model: 模型名称


            base_url: API基础URL


            max_retries: 最大重试次数


            retry_delay: 重试间隔(秒)


        """


        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY") or "sk-uvbjgxuaigsbjpebfthckspmnpfjixhwuwapwsrrqprfvarl"


        self.model = model


        self.base_url = base_url


        self.max_retries = max_retries


        self.retry_delay = retry_delay


        


        # 验证API密钥格式


        if not self.api_key.startswith("sk-"):


            logger.warning("API密钥格式可能不正确，请检查")


        


        logger.info(f"DeepSeek AI代理初始化完成，模型: {model}")


        


    def generate(self, 


                prompt: str, 


                system_prompt: Optional[str] = None,


                temperature: float = 0.7, 


                max_tokens: int = 1000,


                stream: bool = False,


                full_response: bool = False) -> Union[str, Dict[str, Any]]:


        """


        生成文本


        


        Args:


            prompt: 用户提示词


            system_prompt: 系统提示词，定义AI角色


            temperature: 温度参数，控制创造性 (0.0-1.0)


            max_tokens: 最大生成token数


            stream: 是否使用流式响应


            full_response: 是否返回完整的API响应


            


        Returns:


            生成的文本或完整响应


        """


        # 构建消息


        messages = []


        if system_prompt:


            messages.append({"role": "system", "content": system_prompt})


        messages.append({"role": "user", "content": prompt})


        


        # 生成请求载荷


        payload = {


            "model": self.model,


            "messages": messages,


            "temperature": temperature,


            "max_tokens": max_tokens,


            "stream": stream


        }


        


        # 设置请求头


        headers = {


            "Authorization": f"Bearer {self.api_key}",


            "Content-Type": "application/json"


        }


        


        # 发送请求


        for attempt in range(self.max_retries):


            try:


                logger.debug(f"发送请求到DeepSeek API, 尝试 {attempt+1}/{self.max_retries}")


                


                response = requests.post(


                    f"{self.base_url}/chat/completions",


                    headers=headers,


                    json=payload,


                    timeout=60


                )


                


                # 检查响应状态


                response.raise_for_status()


                result = response.json()


                


                if full_response:


                    return result


                else:


                    return result["choices"][0]["message"]["content"]


                    


            except requests.exceptions.Timeout:


                logger.warning(f"请求超时，尝试 {attempt+1}/{self.max_retries}")


                if attempt < self.max_retries - 1:


                    time.sleep(self.retry_delay)


                    


            except Exception as e:


                logger.warning(f"请求失败: {str(e)}")


                if attempt < self.max_retries - 1:


                    time.sleep(self.retry_delay)


                    


        # 达到最大重试次数后仍失败


        logger.error("达到最大重试次数，请求失败")


        raise Exception("无法连接DeepSeek API")


        


    def analyze_market(self, 


                      market_data: Dict[str, Any],


                      question: str = "分析当前市场状况") -> Dict[str, Any]:


        """


        分析市场数据


        


        Args:


            market_data: 市场数据字典


            question: 分析问题


            


        Returns:


            分析结果字典


        """


        # 构建提示词


        system_prompt = """你是一位专业的量化分析师，擅长技术分析和市场研判。


请基于提供的市场数据，给出专业、简洁的分析意见。


回答要点：


1. 关键技术指标解读


2. 市场趋势判断


3. 潜在交易机会


4. 风险提示"""


        


        market_context = json.dumps(market_data, indent=2, ensure_ascii=False)


        prompt = f"{question}\n\n市场数据：\n{market_context}"


        


        try:


            analysis = self.generate(


                prompt=prompt,


                system_prompt=system_prompt,


                temperature=0.4  # 使用较低温度保持分析客观


            )


            


            return {


                "status": "success",


                "analysis": analysis,


                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")


            }


            


        except Exception as e:


            logger.error(f"市场分析失败: {str(e)}")


            return {


                "status": "error",


                "message": str(e)


            }


            


    def generate_strategy(self, 


                         strategy_type: str,


                         reason: str,


                         market_context: Optional[Dict[str, str]] = None) -> Dict[str, Any]:


        """


        生成交易策略


        


        Args:


            strategy_type: 策略类型 ('momentum', 'mean_reversion', 等)


            reason: 策略改进的原因


            market_context: 市场上下文


            


        Returns:


            生成的策略代码和元数据


        """


        # 构建市场上下文


        context_text = ""


        if market_context:


            context_text = """


当前市场状况：


- 市场类型: {market_type}


- 波动率水平: {volatility_level}


- 关键支撑位: {support}


- 关键阻力位: {resistance}


- 近期异常事件: {recent_events}


""".format(


                market_type=market_context.get("market_type", "未知"),


                volatility_level=market_context.get("volatility_level", "中"),


                support=market_context.get("support", "未知"),


                resistance=market_context.get("resistance", "未知"),


                recent_events=market_context.get("recent_events", "无")


            )


            


        # 构建策略类型提示


        strategy_type_text = f"\n请生成一个{strategy_type}类型的策略。" if strategy_type else ""


            


        # 构建完整提示词


        system_prompt = "你是一个专业的量化交易策略专家，能够编写高质量的交易策略代码"


        


        prompt = f"""


你是一个专业量化研究员。以下是最近一次策略回测失败的原因：


{reason}





请根据失败原因，提出新的策略思路。要求：


1. 基于回测失败的具体原因，设计一个新的交易策略


2. 策略需要继承自Strategy基类


3. 请实现完整的Python代码，包含以下内容：


   - 类定义：继承自Strategy


   - __init__方法：接受name、symbols和params参数


   - 关键技术指标计算


   - 信号生成逻辑


   - 执行逻辑





{context_text}


{strategy_type_text}





请提供完整的策略类实现。这个策略会被直接导入到我们的系统中运行。


只返回完整的Python代码，不需要解释说明。


"""


        


        try:


            # 生成策略代码


            strategy_code = self.generate(


                prompt=prompt,


                system_prompt=system_prompt,


                temperature=0.7,


                max_tokens=2000


            )


            


            # 提取纯代码部分


            strategy_code = self._extract_code_from_response(strategy_code)


                


            # 从生成的代码中提取策略名称


            strategy_name = self._extract_strategy_name(strategy_code)


                


            # 构造结果


            result = {


                "code": strategy_code,


                "meta": {


                    "name": strategy_name,


                    "description": f"基于以下原因生成的策略: {reason[:100]}...",


                    "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),


                    "model": self.model,


                    "strategy_type": strategy_type,


                    "prompt": {


                        "reason": reason,


                        "market_context": market_context,


                        "strategy_type": strategy_type


                    },


                    "performance": {}  # 将由回测填充


                }


            }


            


            return result


            


        except Exception as e:


            logger.error(f"生成策略失败: {str(e)}")


            return {


                "status": "error",


                "message": str(e)


            }


    


    def daily_research(self, topics: List[str] = None) -> Dict[str, Any]:


        """


        生成每日研究报告


        


        Args:


            topics: 研究主题列表


            


        Returns:


            研究报告字典


        """


        if not topics:


            topics = ["市场趋势", "板块轮动", "资金流向", "宏观经济", "明日机会"]


            


        # 构建提示词


        system_prompt = """你是一位专业的市场研究员，每日为量化交易团队提供市场研究报告。


你的报告应当简洁、客观，并提供有价值的投资洞见。"""


        


        prompt = f"""


请生成今日({time.strftime('%Y-%m-%d')})市场研究报告，涵盖以下主题：


{', '.join(topics)}





针对每个主题，请提供：


1. 客观分析


2. 关键数据点


3. 可操作的投资建议





格式要求：


- 报告标题


- 简短执行摘要


- 分主题详细分析


- 总结与明日展望


"""


        


        try:


            report = self.generate(


                prompt=prompt,


                system_prompt=system_prompt,


                temperature=0.6,


                max_tokens=2000


            )


            


            return {


                "status": "success",


                "title": f"市场研究日报 ({time.strftime('%Y-%m-%d')})",


                "content": report,


                "topics": topics,


                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")


            }


            


        except Exception as e:


            logger.error(f"生成研究报告失败: {str(e)}")


            return {


                "status": "error",


                "message": str(e)


            }


            


    def analyze_chart(self, 


                     symbol: str, 


                     chart_data: Dict[str, Any],


                     time_frame: str = "daily") -> Dict[str, Any]:


        """


        分析图表


        


        Args:


            symbol: 股票代码


            chart_data: 图表数据 


            time_frame: 时间周期


            


        Returns:


            图表分析结果


        """


        # 构建提示词


        system_prompt = """你是一位专业的技术分析师，擅长解读价格图表和技术指标。


请基于提供的图表数据，给出简洁、专业的分析意见。"""


        


        # 转换图表数据为文本描述


        chart_description = f"""


图表数据 ({symbol}, {time_frame}):


- 时间范围: {chart_data.get('date_range', '未知')}


- 当前价格: {chart_data.get('current_price', '未知')}


- 今日涨跌幅: {chart_data.get('daily_change', '未知')}





技术指标:


- MA(20): {chart_data.get('ma20', '未知')}


- MA(50): {chart_data.get('ma50', '未知')}


- RSI(14): {chart_data.get('rsi', '未知')}


- MACD: {chart_data.get('macd', '未知')}


- 成交量: {chart_data.get('volume', '未知')}





价格形态:


- 支撑位: {chart_data.get('support', '未知')}


- 阻力位: {chart_data.get('resistance', '未知')}


- 趋势状态: {chart_data.get('trend', '未知')}


"""


        


        prompt = f"""


请分析以下图表数据，并提供:


1. 当前市场状况简要评估


2. 关键技术指标分析


3. 价格走势预判


4. 潜在交易机会或风险提示





{chart_description}


"""


        


        try:


            analysis = self.generate(


                prompt=prompt,


                system_prompt=system_prompt,


                temperature=0.4


            )


            


            # 提取关键结论


            conclusion = self._extract_conclusion(analysis)


            


            return {


                "status": "success",


                "symbol": symbol,


                "time_frame": time_frame,


                "analysis": analysis,


                "conclusion": conclusion,


                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")


            }


            


        except Exception as e:


            logger.error(f"图表分析失败: {str(e)}")


            return {


                "status": "error",


                "message": str(e)


            }


            


    def _extract_code_from_response(self, response: str) -> str:


        """从模型响应中提取代码块"""


        # 尝试匹配三重反引号代码块


        code_blocks = re.findall(r'```(?:python)?(.*?)```', response, re.DOTALL)


        


        if code_blocks:


            # 合并所有代码块


            cleaned_code = '\n'.join([block.strip() for block in code_blocks])


            return cleaned_code


        


        # 如果没有代码块，尝试匹配类定义


        class_match = re.search(r'(class\s+\w+\s*\([^)]*\):.*)', response, re.DOTALL)


        if class_match:


            return class_match.group(1)


        


        # 如果以上都失败，返回原始响应


        return response


        


    def _extract_strategy_name(self, code: str) -> str:


        """从代码中提取策略名称"""


        # 查找class关键字后的策略名


        match = re.search(r'class\s+(\w+)', code)


        if match:


            return match.group(1)


        return f"GeneratedStrategy_{int(time.time())}"


    


    def _extract_conclusion(self, analysis: str) -> str:


        """从分析中提取核心结论"""


        # 查找"结论"、"总结"或"建议"部分


        conclusion_match = re.search(r'(?:结论|总结|建议|交易机会|小结)[:：](.*?)(?:\n\n|\Z)', analysis, re.DOTALL)


        if conclusion_match:


            return conclusion_match.group(1).strip()


            


        # 如果没有明确的结论部分，取最后一段


        paragraphs = analysis.split('\n\n')


        if paragraphs:


            return paragraphs[-1].strip()


            


        return "无法提取结论" 