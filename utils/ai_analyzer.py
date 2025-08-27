"""
AI-powered market analysis module using SiliconFlow API
"""

import os
from typing import Dict, Optional, Any
import requests
import pandas as pd
import json
from datetime import datetime
from dotenv import load_dotenv

class AIAnalyzer:
    """AI-powered market analysis using SiliconFlow API"""
    
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in .env file")
        
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.model = "deepseek-chat"  # 使用免费模型

    def _build_market_context(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建市场上下文数据"""
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "market_data": market_data,
            "analysis_type": "option_trading"
        }
    
    def _build_prompt(self, market_context: Dict[str, Any]) -> str:
        """构建专业操盘手风格的 prompt"""
        return f"""你是一位拥有20年经验的美股期权交易专家。请根据以下市场数据进行分析：

市场数据：
{json.dumps(market_context, indent=2, ensure_ascii=False)}

请提供以下分析：
1. 当前市场趋势和情绪分析
2. 技术面和期权链分析
3. 是否存在异常资金行为
4. 交易建议（包括具体的期权策略）

请以JSON格式返回，包含以下字段：
- bias: 市场偏向（BULLISH/NEUTRAL/BEARISH）
- confidence: 置信度（0-1）
- logic_chain: 分析逻辑链
- risk_factors: 风险因素
- suggested_strategy: 建议的期权策略
"""
    
    def _call_llm_api(self, prompt: str) -> Dict[str, Any]:
        """调用 DeepSeek API"""
        try:
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # 解析返回的 JSON 字符串
            return json.loads(content)
            
        except Exception as e:
            print(f"Error calling DeepSeek API: {str(e)}")
            return None
    
    def analyze_market(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """分析市场数据并生成交易信号"""
        try:
            # 构建市场上下文
            market_context = self._build_market_context(symbol, market_data)
            
            # 构建 prompt
            prompt = self._build_prompt(market_context)
            
            # 调用 LLM API
            analysis_result = self._call_llm_api(prompt)
            
            if analysis_result:
                # 添加时间戳
                analysis_result['timestamp'] = datetime.now().isoformat()
                return analysis_result
            
            return None
            
        except Exception as e:
            print(f"Error in market analysis: {str(e)}")
            return None

    def analyze_market_data(self, stock_data: pd.DataFrame) -> Dict:
        """
        Analyze market data using AI
        Args:
            stock_data: DataFrame with OHLCV data
        Returns:
            Dict containing analysis results
        """
        # Prepare market data summary
        latest_data = stock_data.tail(5)
        data_summary = latest_data.to_string()
        
        messages = [
            {"role": "system", "content": "你是一位专业的市场分析师，请基于提供的数据进行分析并给出建议。"},
            {"role": "user", "content": f"""请分析以下市场数据并提供见解：
            
{data_summary}

请从以下几个方面进行分析，并以JSON格式返回（只返回JSON，不要其他内容）：
{{
    "market_trend": "详细分析市场趋势，包括短期和中期走势",
    "support_resistance": "分析关键支撑位和阻力位，给出具体价格",
    "volume_analysis": "分析成交量变化及其含义",
    "trading_signals": "基于以上分析给出具体的交易建议"
}}"""}
        ]

        response = self._call_llm_api(json.dumps(messages))
        
        try:
            if "choices" in response and response["choices"]:
                content = response["choices"][0]["message"]["content"]
                # 尝试清理和格式化JSON字符串
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                analysis = json.loads(content)
            else:
                analysis = {
                    "error": "Invalid API response format",
                    "raw_response": response
                }
        except (json.JSONDecodeError, KeyError) as e:
            analysis = {
                "error": f"Failed to parse AI response: {str(e)}",
                "raw_response": response
            }
            
        return analysis

    def analyze_option_chain(self, option_chain: Dict) -> Dict:
        """
        Analyze option chain data using AI
        Args:
            option_chain: Dict containing calls and puts DataFrames
        Returns:
            Dict containing analysis results
        """
        # Prepare option chain summary
        calls_summary = option_chain['calls'].head().to_string()
        puts_summary = option_chain['puts'].head().to_string()
        
        messages = [
            {"role": "system", "content": "你是一位专业的期权交易员，请基于提供的数据进行分析并给出交易建议。"},
            {"role": "user", "content": f"""请分析以下期权数据并提供交易建议：

看涨期权数据：
{calls_summary}

看跌期权数据：
{puts_summary}

请从以下几个方面进行分析，并以JSON格式返回（只返回JSON，不要其他内容）：
{{
    "sentiment": "分析期权市场情绪，包括看涨看跌比率和成交量分布",
    "volatility": "分析隐含波动率水平及趋势",
    "strategies": "推荐具体的期权交易策略，包括选择哪个到期日、行权价和具体操作",
    "risk_assessment": "评估当前市场风险和建议的止损止盈位置"
}}"""}
        ]

        response = self._call_llm_api(json.dumps(messages))
        
        try:
            if "choices" in response and response["choices"]:
                content = response["choices"][0]["message"]["content"]
                # 尝试清理和格式化JSON字符串
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                analysis = json.loads(content)
            else:
                analysis = {
                    "error": "Invalid API response format",
                    "raw_response": response
                }
        except (json.JSONDecodeError, KeyError) as e:
            analysis = {
                "error": f"Failed to parse AI response: {str(e)}",
                "raw_response": response
            }
            
        return analysis 

if __name__ == "__main__":
    # 测试代码
    analyzer = AIAnalyzer()
    
    # 示例市场数据
    test_market_data = {
        "price": 150.25,
        "rsi": 65.5,
        "macd": 0.5,
        "volume": 1000000,
        "iv": 0.35,
        "put_call_ratio": 0.8
    }
    
    # 运行分析
    result = analyzer.analyze_market("AAPL", test_market_data)
    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False)) 