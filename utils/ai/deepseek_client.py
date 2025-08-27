"""
DeepSeek AI API Client
"""
import os
import json
import requests

class DeepSeekClient:
    """DeepSeek client implementation"""
    
    def __init__(self, api_key=None, api_base=None, model=None):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.api_base = api_base or os.environ.get("DEEPSEEK_API_BASE") or "https://api.siliconflow.cn/v1"
        self.model = model or os.environ.get("DEEPSEEK_MODEL") or "deepseek-ai/DeepSeek-V3"
        
    def completion(self, prompt, model=None, temperature=0.7, max_tokens=2000):
        """Generate text completion"""
        if not self.api_key:
            return {"error": "API key not set"}
        
        model_to_use = model or self.model
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model_to_use,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            endpoint = f"{self.api_base}/chat/completions"
            print(f"Calling API: {endpoint}")
            print(f"Using model: {model_to_use}")
            
            response = requests.post(
                endpoint, 
                headers=headers, 
                json=data,
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"API error: {response.status_code}")
                print(f"Response: {response.text}")
                return {"error": f"API call failed: HTTP {response.status_code}"}
                
            return response.json()
        except Exception as e:
            print(f"Call exception: {str(e)}")
            return {"error": f"API call failed: {str(e)}"}

def create_client(api_key=None, api_base=None, model=None):
    """Create client"""
    return DeepSeekClient(api_key, api_base, model)
