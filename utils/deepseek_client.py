import os
import requests
import logging
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DeepSeekClient")

class DeepSeekClient:
    """
    Client for accessing DeepSeek AI API
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the DeepSeek client
        
        Args:
            api_key: DeepSeek API key. If not provided, tries to load from
                    environment variable DEEPSEEK_API_KEY
        """
        # Load environment variables
        load_dotenv()
        
        # Use provided API key or get from environment
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.is_mock_mode = False
        
        if not self.api_key:
            logger.warning("DeepSeek API key not provided and not found in environment. Using mock mode.")
            self.is_mock_mode = True
            
        # API endpoint
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        
        # Request headers
        self.headers = {
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
            "Content-Type": "application/json"
        }
        
    def analyze(self, prompt: str, model: str = "deepseek-chat") -> str:
        """
        Send a prompt to DeepSeek API for analysis
        
        Args:
            prompt: The prompt text to analyze
            model: DeepSeek model to use
            
        Returns:
            Response content as string
        """
        if self.is_mock_mode:
            return self._get_mock_response(prompt)
        
        try:
            # Prepare request data
            data = {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            # Send request
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            # Check for authentication errors
            if response.status_code == 401:
                logger.error("DeepSeek API authentication failed. Using mock mode.")
                self.is_mock_mode = True
                return self._get_mock_response(prompt)
            
            # Check for other errors
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            
            # Extract content from response
            content = result["choices"][0]["message"]["content"]
            
            return content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {str(e)}")
            # Fall back to mock mode
            self.is_mock_mode = True
            return self._get_mock_response(prompt)
            
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing API response: {str(e)}")
            return self._get_mock_response(prompt)
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return self._get_mock_response(prompt)
            
    def _get_mock_response(self, prompt: str) -> str:
        """
        Generate a mock response when API is unavailable
        
        Args:
            prompt: The original prompt
            
        Returns:
            A mock response as string
        """
        logger.info("Generating mock response for prompt")
        
        # Check if the prompt seems to be about trading strategy
        if "交易策略" in prompt or "期权" in prompt or "股票" in prompt:
            mock_data = {
                "action": "Hold",
                "confidence": 0.65,
                "risk_level": "中",
                "expected_move": "+2.5%",
                "reason": "这是一个模拟响应，因为DeepSeek API未配置或不可用",
                "strike_price": 190.50,
                "stop_loss": 182.30,
                "ai_rating": "B"
            }
            
            # Check if we can infer a symbol from the prompt
            if "symbol" in prompt.lower():
                for line in prompt.split("\n"):
                    if "symbol" in line.lower() and ":" in line:
                        symbol = line.split(":", 1)[1].strip()
                        mock_data["symbol"] = symbol
            
            return json.dumps(mock_data, ensure_ascii=False)
        else:
            # Generic response for other types of prompts
            return "无法连接到DeepSeek API，请检查API密钥设置或网络连接。" 