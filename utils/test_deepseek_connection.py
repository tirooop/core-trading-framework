#!/usr/bin/env python
"""
DeepSeek API Connection Test

This script tests the connection to the DeepSeek AI API and verifies that the API key works.
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime

def test_deepseek_connection(api_key, api_base, model):
    """
    Test connection to DeepSeek API
    
    Args:
        api_key: DeepSeek API key
        api_base: DeepSeek API base URL
        model: DeepSeek model name
        
    Returns:
        True if connection successful, False otherwise
    """
    print(f"Testing connection to DeepSeek API at {api_base}")
    print(f"Using model: {model}")
    
    if not api_key:
        print("Error: API key is not set")
        return False
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Test prompt
    prompt = "Hello, I'm testing the connection to the DeepSeek API. Please respond with a short message indicating the connection is working."
    
    # Prepare the API request
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 100
    }
    
    # Endpoint for chat completions
    endpoint = f"{api_base}/chat/completions"
    
    try:
        print(f"Sending test request to {endpoint}...")
        start_time = datetime.now()
        
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        if response.status_code == 200:
            result = response.json()
            
            if "choices" in result and result["choices"]:
                content = result["choices"][0]["message"]["content"]
                
                print(f"\n✅ Connection Successful! ({elapsed:.2f}s)")
                print(f"\nResponse from DeepSeek AI:")
                print(f"{content}\n")
                
                print("API Response Details:")
                if "model" in result:
                    print(f"  Model: {result['model']}")
                if "usage" in result:
                    usage = result["usage"]
                    print(f"  Tokens: {usage.get('total_tokens', 'N/A')} total, "
                          f"{usage.get('prompt_tokens', 'N/A')} prompt, "
                          f"{usage.get('completion_tokens', 'N/A')} completion")
                
                return True
            else:
                print("\n❌ Error: Received response but no content")
                print(f"Response: {json.dumps(result, indent=2)}")
                return False
        else:
            print(f"\n❌ Error: Received status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Connection Error: {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected Error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test DeepSeek API Connection")
    parser.add_argument("--api-key", type=str, default=os.environ.get("DEEPSEEK_API_KEY", ""),
                        help="DeepSeek API key (or set DEEPSEEK_API_KEY env var)")
    parser.add_argument("--api-base", type=str, default="https://api.siliconflow.cn/v1",
                        help="DeepSeek API base URL")
    parser.add_argument("--model", type=str, default="deepseek-ai/DeepSeek-V3",
                        help="DeepSeek model name")
    parser.add_argument("--config", type=str, default=None,
                        help="Path to config file (to load API settings)")
    
    args = parser.parse_args()
    
    # If config file provided, try to load API key from there
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
                
            ai_config = config.get("ai_analyzer", {}).get("ai_config", {})
            if not args.api_key and "api_key" in ai_config:
                args.api_key = ai_config["api_key"]
                print(f"Loaded API key from config file: {args.config}")
            
            if "api_base" in ai_config:
                args.api_base = ai_config["api_base"]
                print(f"Loaded API base URL from config file: {args.api_base}")
                
            if "model" in ai_config:
                args.model = ai_config["model"]
                print(f"Loaded model from config file: {args.model}")
                
        except Exception as e:
            print(f"Warning: Error loading config file: {str(e)}")
    
    # Test connection
    success = test_deepseek_connection(args.api_key, args.api_base, args.model)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 