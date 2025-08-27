"""
DeepSeek API 工具模块
提供与DeepSeek AI模型交互的工具函数
支持文本生成、对话和分析功能
"""

import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

def get_deepseek_response(
    prompt: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 500,
    temperature: float = 0.7,
    system_prompt: Optional[str] = None
) -> str:
    """
    向DeepSeek API发送请求并获取回复
    
    Args:
        prompt: 用户提示
        api_key: DeepSeek API密钥，如不提供则从环境变量获取
        model: DeepSeek模型名称，如不提供则使用默认模型
        max_tokens: 最大生成token数量
        temperature: 温度参数，影响生成多样性
        system_prompt: 系统提示，为模型提供上下文
        
    Returns:
        模型生成的文本
    """
    # 获取API密钥和URL
    api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
    api_url = os.environ.get("DEEPSEEK_API_URL", "https://api.siliconflow.cn/v1")
    model = model or os.environ.get("DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-V3")
    
    if not api_key:
        logger.error("未提供DeepSeek API密钥")
        return "无法连接DeepSeek API：未提供API密钥"
    
    # 准备请求
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 构建消息
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    # 请求体
    data = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    try:
        response = requests.post(
            f"{api_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                return content
            else:
                logger.error(f"DeepSeek API响应格式错误: {result}")
                return "DeepSeek API返回了空响应"
        else:
            logger.error(f"DeepSeek API请求失败: 状态码 {response.status_code}, 响应: {response.text}")
            return f"DeepSeek API请求失败: {response.text}"
            
    except Exception as e:
        logger.error(f"请求DeepSeek API时出错: {str(e)}")
        return f"请求DeepSeek API时出错: {str(e)}"

def generate_strategy(
    strategy_type: str,
    parameters: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    生成交易策略
    
    Args:
        strategy_type: 策略类型（如"mean_reversion", "momentum", "breakout"等）
        parameters: 策略参数
        api_key: DeepSeek API密钥，如不提供则从环境变量获取
        
    Returns:
        生成的策略代码和说明的字典
    """
    # 获取API密钥
    api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
    
    # 构建提示
    system_prompt = """你是一位专业的量化交易策略开发专家。请严格按照用户的请求生成高质量的量化交易策略代码。
代码应该具有以下特点：
1. 简洁清晰，注释得当
2. 遵循Python最佳实践
3. 仅使用常见的库（pandas, numpy, talib等）
4. 适合实际交易环境
5. 包含必要的风险管理机制"""

    # 构建策略描述
    strategy_descriptions = {
        "mean_reversion": "均值回归策略，在价格偏离均值时寻找回归机会",
        "momentum": "动量策略，追踪价格趋势方向",
        "breakout": "突破策略，在价格突破关键水平时交易",
        "volatility": "波动率策略，利用市场波动性变化",
        "options_gamma": "期权gamma策略，利用期权特性对冲风险获利"
    }
    
    description = strategy_descriptions.get(strategy_type, f"{strategy_type}策略")
    
    # 构建参数说明
    params_text = ""
    if parameters:
        params_text = "参数要求:\n"
        for key, value in parameters.items():
            params_text += f"- {key}: {value}\n"
    
    prompt = f"""请生成一个{description}的Python实现。

{params_text}

请提供完整的策略类实现，包括：
1. 初始化方法
2. 信号生成逻辑
3. 入场和出场条件
4. 风险管理机制

代码应可在实际量化交易系统中使用，请使用标准的pandas数据格式输入。
"""

    try:
        # 获取响应
        response = get_deepseek_response(
            prompt=prompt,
            api_key=api_key,
            max_tokens=1000,
            temperature=0.2,
            system_prompt=system_prompt
        )
        
        # 提取代码部分
        code = ""
        in_code_block = False
        code_blocks = []
        
        for line in response.split('\n'):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                if not in_code_block:  # 结束代码块
                    code_blocks.append(code)
                    code = ""
                continue
            if in_code_block:
                code += line + "\n"
        
        # 合并所有代码块
        final_code = "\n".join(code_blocks) if code_blocks else response
        
        return {
            "success": True,
            "strategy_type": strategy_type,
            "code": final_code,
            "description": description
        }
        
    except Exception as e:
        logger.error(f"生成策略时出错: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def analyze_performance(
    performance_data: Dict[str, Any],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    分析策略性能
    
    Args:
        performance_data: 性能数据字典
        api_key: DeepSeek API密钥，如不提供则从环境变量获取
        
    Returns:
        分析结果字典
    """
    # 获取API密钥
    api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
    
    # 系统提示
    system_prompt = """你是一位专业的量化策略分析师。请基于提供的性能数据，提供简洁、专业、有见地的分析和建议。
你的分析应该关注关键指标、风险因素和潜在的改进方向。"""

    # 构建提示
    prompt = "请分析以下量化交易策略的性能数据：\n\n"
    prompt += json.dumps(performance_data, indent=2, ensure_ascii=False)
    prompt += """

请提供以下分析：
1. 策略优势和不足
2. 主要风险因素
3. 基于数据的优化建议
4. 对未来表现的预测

分析应简洁明了，重点突出关键发现和建议。
"""

    try:
        # 获取响应
        response = get_deepseek_response(
            prompt=prompt,
            api_key=api_key,
            max_tokens=500,
            temperature=0.4,
            system_prompt=system_prompt
        )
        
        return {
            "success": True,
            "analysis": response
        }
        
    except Exception as e:
        logger.error(f"分析性能时出错: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# 测试代码
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 测试API连接
    test_prompt = "简述量化交易中的均值回归策略"
    
    print("测试DeepSeek API连接...")
    response = get_deepseek_response(test_prompt, max_tokens=150)
    print(f"响应内容: {response}")
    
    # 测试策略生成
    print("\n测试策略生成...")
    strategy_result = generate_strategy(
        strategy_type="mean_reversion",
        parameters={"lookback_period": 20, "std_dev": 2.0}
    )
    
    if strategy_result["success"]:
        print(f"生成的策略代码:\n{strategy_result['code'][:200]}...(已截断)")
    else:
        print(f"生成策略失败: {strategy_result.get('error')}") 