# OpenAI API Client

import os
import json
import time
import requests

class OpenAIClient:
    """Simplified OpenAI client implementation"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.api_base = "https://api.openai.com/v1"
        
    def completion(self, prompt, model="gpt-3.5-turbo", temperature=0.7, max_tokens=2000):
        """Generate text completion"""
        if not self.api_key:
            return {"error": "API key not set, please set OPENAI_API_KEY in .env file"}
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/chat/completions", 
                headers=headers, 
                json=data,
                timeout=60
            )
            return response.json()
        except Exception as e:
            return {"error": f"API call failed: {str(e)}"}

# Convenience function
def create_client(api_key=None):
    """Create client"""
    return OpenAIClient(api_key)


