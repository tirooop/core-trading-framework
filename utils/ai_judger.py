import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ai_judger.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AIJudger")

DEEPSEEK_PROMPT_TEMPLATE = """
你是专业的期权交易专家，请根据以下市场与策略数据，判断是否发出交易信号：

股票代码: {symbol}
当前价格: {current_price}
目标价格: {target_price}
止损价格: {stop_loss}
风险收益比: {risk_reward}
置信度: {confidence}
板块走势（%）: {sector_performance}
期权市场: {option_flow}

请分析上述市场数据并给出完整的期权交易决策，包括行动建议、风险评级和预期移动。

请以JSON格式返回：
{{
    "notify": "是/否",
    "action": "Call/Put/Hold",
    "confidence": 0-1之间的浮点数,
    "risk_level": "低/中/高",
    "expected_move": "+X%/-X%",
    "reason": "简洁理由（不超过两行）",
    "ai_rating": "A/B/C"
}}

其中：
- notify：是否应该通知用户
- action：推荐的期权类型（Call看涨/Put看跌/Hold观望）
- confidence：AI对该推荐的置信度（0-1之间）
- risk_level：交易风险等级（低/中/高）
- expected_move：预期价格变动（百分比）
- reason：推荐理由（简洁明了）
- ai_rating：AI给出的信号质量评级（A最高/C最低）
"""

class AIJudger:
    """
    使用DeepSeek AI判断是否应该发送期权交易通知
    并生成专业化的交易建议
    """
    
    def __init__(self, deepseek_client=None):
        """
        初始化AI判断器
        
        Args:
            deepseek_client: DeepSeek API客户端实例
        """
        self.client = deepseek_client
        
    def judge(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        判断是否应该发送通知并生成交易建议
        
        Args:
            context: 包含策略执行结果和市场数据的上下文
            
        Returns:
            字典包含通知决策和建议
        """
        try:
            # 填充prompt模板
            prompt = DEEPSEEK_PROMPT_TEMPLATE.format(**context)
            
            # 调用DeepSeek API
            response = self.client.analyze(prompt)
            
            # 解析返回的JSON
            try:
                result = json.loads(response)
                
                # 记录AI决策
                logger.info(f"AI decision for {context.get('symbol')}: {result}")
                
                # 确保返回数据格式正确
                required_fields = ["notify", "action", "confidence", "risk_level", "expected_move", "reason", "ai_rating"]
                missing_fields = [field for field in required_fields if field not in result]
                
                if missing_fields:
                    logger.warning(f"AI response missing required fields: {missing_fields}")
                    for field in missing_fields:
                        if field == "notify":
                            result["notify"] = "否"
                        elif field == "action":
                            result["action"] = "Hold"
                        elif field == "confidence":
                            result["confidence"] = 0.5
                        elif field == "risk_level":
                            result["risk_level"] = "中"
                        elif field == "expected_move":
                            result["expected_move"] = "0%"
                        elif field == "reason":
                            result["reason"] = "AI分析结果缺失关键信息"
                        elif field == "ai_rating":
                            result["ai_rating"] = "C"
                
                return result
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse AI response as JSON: {response}")
                return {
                    "notify": "否", 
                    "action": "Hold", 
                    "confidence": 0.0,
                    "risk_level": "高",
                    "expected_move": "0%",
                    "reason": "AI解析失败，无法处理返回格式",
                    "ai_rating": "C"
                }
                
        except Exception as e:
            logger.error(f"Error during AI judgment: {str(e)}")
            return {
                "notify": "否", 
                "action": "Hold", 
                "confidence": 0.0,
                "risk_level": "高",
                "expected_move": "0%",
                "reason": f"AI判断过程发生错误: {str(e)}",
                "ai_rating": "C"
            }
            
    def get_formatted_result(self, ai_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        将AI结果转换为统一格式，用于通知系统
        
        Args:
            ai_result: AI判断结果
            context: 原始上下文数据
            
        Returns:
            格式化后的结果字典
        """
        # 合并原始上下文和AI结果
        result = {**context}
        
        # 添加AI判断结果
        result["notify"] = ai_result.get("notify", "否")
        result["action"] = ai_result.get("action", "Hold")
        result["confidence"] = ai_result.get("confidence", 0.0)
        result["risk_level"] = ai_result.get("risk_level", "中")
        result["expected_move"] = ai_result.get("expected_move", "0%")
        result["reason"] = ai_result.get("reason", "")
        result["ai_rating"] = ai_result.get("ai_rating", "C")
        
        # 添加时间戳
        result["timestamp"] = datetime.now().isoformat()
        
        # 转换期权类型为标准格式
        if result["action"].lower() == "call":
            result["option_type"] = "call"
            result["direction"] = "BULLISH"
        elif result["action"].lower() == "put":
            result["option_type"] = "put"
            result["direction"] = "BEARISH"
        else:
            result["option_type"] = "hold"
            result["direction"] = "NEUTRAL"
            
        return result 