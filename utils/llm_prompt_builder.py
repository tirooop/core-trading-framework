from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import os
import json
import logging
from dotenv import load_dotenv
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class MarketContext:
    """Market context data class"""
    symbol: str
    price: float
    rsi: float
    macd: float
    ema20: float
    ema50: float
    vix: float
    volume_ratio: float
    sentiment_summary: str
    sector: str
    sector_strength: float
    news: List[str]
    index_diff: float

class LLMPromptBuilder:
    """LLM Prompt Builder"""
    
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in .env file")
        
        self.api_url = "https://api.siliconflow.cn/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Define strategy templates
        self.strategy_templates = {
            "TREND_BREAKOUT": {
                "conditions": ["RSI > 65", "MACD Golden Cross", "Volume Surge"],
                "strategy": "Buy ATM CALL",
                "description": "Trend Breakout Strategy"
            },
            "TREND_REVERSAL": {
                "conditions": ["RSI < 40", "MACD Death Cross", "EMA20 Crosses Below EMA50"],
                "strategy": "Buy ATM PUT",
                "description": "Trend Reversal Strategy"
            },
            "RANGE_TRADING": {
                "conditions": ["RSI Between 40-60", "No Clear Sector Advantage"],
                "strategy": "Sell STRADDLE",
                "description": "Range Trading Strategy"
            },
            "SHORT_SQUEEZE": {
                "conditions": ["Daily Gain > 8%", "SPY Gain < 1%"],
                "strategy": "SELL CALL",
                "description": "Short Squeeze Strategy"
            }
        }
        
    def build_market_analysis_prompt(self, market_data: Dict[str, Any]) -> str:
        """
        Build market analysis prompt
        
        Args:
            market_data: Market data dictionary
            
        Returns:
            Formatted prompt
        """
        prompt = f"""
Please analyze the following market data and provide insights:

Market Data:
{json.dumps(market_data, indent=2)}

Please provide:
1. Market trend analysis
2. Key support/resistance levels
3. Volume analysis
4. Technical indicator interpretation
5. Risk assessment
6. Trading recommendations
"""
        return prompt
        
    def build_strategy_prompt(self, strategy_type: str, market_data: Dict[str, Any]) -> str:
        """
        Build strategy generation prompt
        
        Args:
            strategy_type: Type of strategy to generate
            market_data: Market data dictionary
            
        Returns:
            Formatted prompt
        """
        template = self.strategy_templates.get(strategy_type)
        if not template:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
            
        prompt = f"""
Please generate a trading strategy based on the following:

Strategy Type: {strategy_type}
Description: {template['description']}

Market Data:
{json.dumps(market_data, indent=2)}

Required Conditions:
{json.dumps(template['conditions'], indent=2)}

Please provide:
1. Entry conditions
2. Exit conditions
3. Position sizing
4. Risk management rules
5. Expected performance metrics
"""
        return prompt

    def _call_deepseek_api(self, prompt: str) -> Optional[Dict[str, Any]]:
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

    def analyze_market(self, context: MarketContext) -> Optional[Dict[str, Any]]:
        """分析市场数据"""
        try:
            # 构建市场分析提示词
            prompt = self.build_market_analysis_prompt(context.__dict__)
            
            # 调用 API
            analysis_result = self._call_deepseek_api(prompt)
            
            if analysis_result:
                # 添加时间戳
                analysis_result['timestamp'] = datetime.now().isoformat()
                return analysis_result
            
            return None
            
        except Exception as e:
            print(f"Error in market analysis: {str(e)}")
            return None

    def analyze_strategy(self, context: MarketContext, template_name: str) -> Optional[Dict[str, Any]]:
        """分析特定策略"""
        try:
            # 构建策略提示词
            prompt = self.build_strategy_prompt(template_name, context.__dict__)
            
            # 调用 API
            strategy_result = self._call_deepseek_api(prompt)
            
            if strategy_result:
                # 添加时间戳
                strategy_result['timestamp'] = datetime.now().isoformat()
                return strategy_result
            
            return None
            
        except Exception as e:
            print(f"Error in strategy analysis: {str(e)}")
            return None

if __name__ == "__main__":
    # 测试代码
    prompt_builder = LLMPromptBuilder()
    
    # 示例市场数据
    test_context = MarketContext(
        symbol="AAPL",
        price=150.25,
        rsi=65.5,
        macd=0.5,
        ema20=148.3,
        ema50=145.8,
        vix=15.2,
        volume_ratio=1.2,
        sentiment_summary="市场情绪偏多，但需警惕回调风险",
        sector="Technology",
        sector_strength=0.8,
        news=["苹果发布新产品", "分析师上调目标价"],
        index_diff=0.5
    )
    
    # 运行市场分析
    analysis_result = prompt_builder.analyze_market(test_context)
    if analysis_result:
        print(json.dumps(analysis_result, indent=2, ensure_ascii=False))
    
    # 运行策略分析
    strategy_result = prompt_builder.analyze_strategy(test_context, "TREND_BREAKOUT")
    if strategy_result:
        print(json.dumps(strategy_result, indent=2, ensure_ascii=False)) 