"""
Qwen Client - Interface for DeepSeek's Qwen model API
"""

import os
import json
import logging
from typing import Dict, List, Optional, Union, Any
import requests
from dotenv import load_dotenv

# Load .env file
load_dotenv()

logger = logging.getLogger(__name__)

class QwenClient:
    """Client for interacting with DeepSeek's Qwen model API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Qwen API client
        
        Args:
            api_key: DeepSeek API key. If not provided, will try to load from DEEPSEEK_API_KEY env var
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            logger.warning("No DeepSeek API key provided. Set DEEPSEEK_API_KEY environment variable.")
        
        self.api_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.model = "Qwen/QwQ-32B"  # Default model
    
    def chat_completion(self, 
                       prompt: str, 
                       system_prompt: Optional[str] = None,
                       temperature: float = 0.7, 
                       max_tokens: int = 512,
                       stream: bool = False) -> Dict[str, Any]:
        """
        Send a chat completion request to the Qwen API
        
        Args:
            prompt: User query/prompt
            system_prompt: Optional system instructions
            temperature: Temperature for sampling (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            stream: Whether to stream the response
            
        Returns:
            API response as a dictionary
        """
        if not self.api_key:
            logger.error("Cannot make API call: No API key provided")
            return {"error": "No API key provided"}
        
        # Build the messages list
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare the payload
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "max_tokens": max_tokens,
            "enable_thinking": False,
            "thinking_budget": 512,
            "min_p": 0.05,
            "stop": None,
            "temperature": temperature,
            "top_p": 0.7,
            "top_k": 50,
            "frequency_penalty": 0.5,
            "n": 1,
            "response_format": {"type": "text"}
        }
        
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            # Make the API request
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            return {"error": str(e)}
        except json.JSONDecodeError:
            logger.error("Failed to parse API response as JSON")
            return {"error": "Invalid JSON response from API"}
    
    def analyze_market(self, symbol: str, price_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market data for a specific symbol
        
        Args:
            symbol: Trading symbol (e.g., 'AAPL')
            price_data: Dictionary containing price information
            
        Returns:
            Analysis results
        """
        prompt = f"""Analyze the following market data for {symbol}:
        
Current Price: ${price_data.get('current_price', 'N/A')}
Previous Close: ${price_data.get('previous_close', 'N/A')}
Volume: {price_data.get('volume', 'N/A')}
52-Week High: ${price_data.get('high_52week', 'N/A')}
52-Week Low: ${price_data.get('low_52week', 'N/A')}

Provide a concise market analysis focusing on:
1. Current trend direction
2. Key support and resistance levels
3. Volume analysis
4. Recommendation (bullish, bearish, or neutral stance)
5. Options trading strategy recommendation if applicable

Format your response as JSON with the following structure:
{
  "trend": "BULLISH/BEARISH/NEUTRAL",
  "support_levels": [level1, level2],
  "resistance_levels": [level1, level2],
  "volume_analysis": "your analysis here",
  "recommendation": "your recommendation here",
  "options_strategy": {
    "type": "CALL/PUT/SPREAD",
    "strike": float,
    "expiry_days": int,
    "confidence": float
  }
}
"""
        
        system_prompt = "You are an expert financial analyst specializing in options trading. Provide accurate, concise, and actionable market analysis."
        
        # Get the analysis from the API
        result = self.chat_completion(prompt, system_prompt=system_prompt)
        
        # Parse the content
        try:
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                
                # Extract the JSON part from the content
                try:
                    # Try to parse the content directly first
                    analysis = json.loads(content)
                except json.JSONDecodeError:
                    # If that fails, try to extract JSON from markdown code block
                    import re
                    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        analysis = json.loads(json_str)
                    else:
                        # Fall back to a simple structure
                        analysis = {
                            "error": "Could not parse JSON from response",
                            "raw_response": content
                        }
                
                return analysis
            else:
                return {"error": "No valid response from API", "raw_response": result}
        except Exception as e:
            logger.error(f"Error parsing API response: {str(e)}")
            return {"error": str(e), "raw_response": result}
    
    def recommend_options_strategy(self, 
                                  symbol: str, 
                                  current_price: float, 
                                  market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get options trading strategy recommendations
        
        Args:
            symbol: Trading symbol (e.g., 'AAPL')
            current_price: Current stock price
            market_data: Additional market data
            
        Returns:
            Strategy recommendations
        """
        prompt = f"""Based on the following market data for {symbol}, recommend an options trading strategy:

Current Price: ${current_price}
Market Trend: {market_data.get('trend', 'Unknown')}
Volatility: {market_data.get('volatility', 'Unknown')}
Recent News: {market_data.get('recent_news', 'None')}

Provide your options trading strategy recommendation in JSON format with the following structure:
{{
  "action": "CALL/PUT/SPREAD/HOLD",
  "strike_price": float,
  "expiration_days": int,
  "confidence": float (0-1),
  "reasoning": "Your analysis and reasoning here",
  "risk_level": "LOW/MEDIUM/HIGH",
  "stop_loss": float,
  "take_profit": float
}}
"""
        
        system_prompt = "You are an expert options trader. Provide practical and actionable options trading advice based on the given market data."
        
        # Get the recommendation from the API
        result = self.chat_completion(prompt, system_prompt=system_prompt)
        
        # Parse the content
        try:
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                
                # Extract the JSON part from the content
                try:
                    # Try to parse the content directly first
                    recommendation = json.loads(content)
                except json.JSONDecodeError:
                    # If that fails, try to extract JSON from markdown code block
                    import re
                    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        recommendation = json.loads(json_str)
                    else:
                        # Fall back to a simple structure
                        recommendation = {
                            "error": "Could not parse JSON from response",
                            "raw_response": content
                        }
                
                return recommendation
            else:
                return {"error": "No valid response from API", "raw_response": result}
        except Exception as e:
            logger.error(f"Error parsing API response: {str(e)}")
            return {"error": str(e), "raw_response": result}

# Create a singleton instance for global use
qwen_client = QwenClient()

if __name__ == "__main__":
    # Test the client if run directly
    print("Testing Qwen client...")
    
    test_prompt = "What are the key factors to consider when trading options?"
    response = qwen_client.chat_completion(test_prompt)
    
    print(json.dumps(response, indent=2)) 