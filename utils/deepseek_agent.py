import os
import requests
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import pandas as pd
import numpy as np

class DeepSeekAgent:
    """
    General-purpose DeepSeek AI agent for text generation and analysis tasks.
    """
    
    def __init__(self, model="deepseek-ai/DeepSeek-V3", api_key=None):
        """
        Initialize the DeepSeek agent.
        
        Args:
            model: Model name to use
            api_key: API key for DeepSeek (if None, will try to get from env)
        """
        load_dotenv()
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or "sk-uvbjgxuaigsbjpebfthckspmnpfjixhwuwapwsrrqprfvarl"
        
        self.model = model
        self.base_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def ask(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Ask a question to the DeepSeek model.
        
        Args:
            prompt: User prompt/question
            system_prompt: Optional system prompt to guide the model
            
        Returns:
            The model's response as a string
        """
        # Use default system prompt if none provided
        if system_prompt is None:
            system_prompt = "你是一位专业的金融分析师和量化交易专家，擅长分析市场数据并提供客观、准确的建议。"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        return self._generate(messages)
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        Have a multi-turn conversation with the model.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            
        Returns:
            The model's response as a string
        """
        return self._generate(messages)
    
    def _generate(self, messages: List[Dict[str, str]]) -> str:
        """
        Generate a response from the model.
        
        Args:
            messages: List of message dicts
            
        Returns:
            The model's response text
        """
        data = {
            "model": self.model,
            "messages": messages
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()["choices"][0]["message"]["content"]
            
        except Exception as e:
            # In case of error, return a simple error message
            return f"分析错误: {str(e)[:100]}..."


class DeepSeekAnalyst(DeepSeekAgent):
    """DeepSeek-powered market analysis assistant."""
    
    def __init__(self, model="deepseek-ai/DeepSeek-V3", api_key=None):
        super().__init__(model, api_key)
    
    def _prepare_market_context(self, df: pd.DataFrame) -> str:
        """Prepare market data context for the model."""
        latest = df.iloc[-1]
        summary = (
            f"最新行情概览：\n"
            f"- 最新价格：${latest['close']:.2f}\n"
            f"- 日内高点：${latest['high']:.2f}\n"
            f"- 日内低点：${latest['low']:.2f}\n"
            f"- 成交量：{latest['volume']:,.0f}\n"
        )
        
        # Calculate basic indicators
        returns = df['close'].pct_change()
        volatility = returns.std() * np.sqrt(252)
        rsi = self._calculate_rsi(df['close'])
        
        technical = (
            f"\n技术指标：\n"
            f"- RSI(14)：{rsi[-1]:.1f}\n"
            f"- 年化波动率：{volatility:.2%}\n"
            f"- 20日均线：${df['close'].rolling(20).mean().iloc[-1]:.2f}\n"
        )
        
        return summary + technical
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def analyze_market(self, 
                      df: pd.DataFrame,
                      question: str,
                      include_data: bool = True) -> Dict[str, Any]:
        """
        Analyze market data using DeepSeek model.
        
        Args:
            df: Market data DataFrame
            question: User's analysis question
            include_data: Whether to include raw data in context
            
        Returns:
            Dict containing model's response and metadata
        """
        # Prepare context
        context = self._prepare_market_context(df)
        if include_data:
            context += f"\n最近行情数据：\n{df.tail(10).to_string()}"
        
        # Prepare prompt
        system_prompt = (
            "你是一位资深量化分析师，擅长技术分析和市场研判。"
            "请基于提供的市场数据，给出专业、简洁的分析意见。"
            "回答要点：\n"
            "1. 关键技术指标解读\n"
            "2. 市场趋势判断\n"
            "3. 潜在交易机会\n"
            "4. 风险提示"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{question}\n\n{context}"}
        ]
        
        try:
            analysis = self.chat(messages)
            
            return {
                "success": True,
                "analysis": analysis,
                "context": context,
                "metadata": {
                    "model": self.model,
                    "timestamp": pd.Timestamp.now().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "context": context
            }

# Create a global instance
analyst = DeepSeekAnalyst() 