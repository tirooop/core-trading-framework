from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class StrategyPromptContext:
    """策略提示词上下文"""
    symbol: str
    timeframes: List[str]
    market_sentiment: str
    volatility: str
    news_summary: str
    sector_strength: str
    technical_indicators: Dict[str, float]
    volume_profile: Dict[str, float]
    options_chain: Dict[str, Any]
    ask: str

class PresetStrategyPrompt:
    """预设策略提示词生成器"""
    
    def __init__(self):
        # 定义市场场景模板
        self.market_scenarios = {
            "TREND_FOLLOWING": {
                "description": "趋势跟踪策略",
                "conditions": [
                    "EMA20 > EMA50",
                    "RSI 在 40-60 之间",
                    "成交量稳定"
                ],
                "prompt_template": """
作为专业期权交易员，请分析以下趋势跟踪机会：

市场数据：
- 股票: {symbol}
- 时间周期: {timeframes}
- 市场情绪: {market_sentiment}
- 波动率: {volatility}
- 板块强度: {sector_strength}

技术指标：
{technical_indicators}

成交量分析：
{volume_profile}

请评估：
1. 趋势强度和持续性
2. 入场时机和止损位置
3. 建议的期权策略

输出JSON格式：
{{
    "trend_analysis": {{
        "strength": "STRONG/MODERATE/WEAK",
        "duration": "SHORT/MEDIUM/LONG",
        "support_levels": [float],
        "resistance_levels": [float]
    }},
    "entry_points": {{
        "price": float,
        "stop_loss": float,
        "take_profit": float
    }},
    "suggested_strategy": {{
        "type": "CALL/PUT/SPREAD",
        "strike": float,
        "expiration_days": int,
        "position_size": "SMALL/MEDIUM/LARGE",
        "risk_level": "LOW/MEDIUM/HIGH"
    }},
    "confidence": 0.0~1.0,
    "risk_factors": [string],
    "logic_chain": [string]
}}
"""
            },
            "BREAKOUT": {
                "description": "突破策略",
                "conditions": [
                    "价格突破关键阻力位",
                    "成交量放大",
                    "RSI > 60"
                ],
                "prompt_template": """
作为专业期权交易员，请分析以下突破机会：

市场数据：
- 股票: {symbol}
- 时间周期: {timeframes}
- 市场情绪: {market_sentiment}
- 波动率: {volatility}
- 板块强度: {sector_strength}

技术指标：
{technical_indicators}

成交量分析：
{volume_profile}

期权链数据：
{options_chain}

请评估：
1. 突破的真实性和强度
2. 是否存在假突破风险
3. 建议的期权策略

输出JSON格式：
{{
    "breakout_analysis": {{
        "type": "PRICE/VOLUME/BOTH",
        "strength": "STRONG/MODERATE/WEAK",
        "confirmation_signals": [string]
    }},
    "risk_assessment": {{
        "fake_breakout_probability": 0.0~1.0,
        "key_levels": [float],
        "stop_loss": float
    }},
    "suggested_strategy": {{
        "type": "CALL/PUT/SPREAD",
        "strike": float,
        "expiration_days": int,
        "position_size": "SMALL/MEDIUM/LARGE",
        "risk_level": "LOW/MEDIUM/HIGH"
    }},
    "confidence": 0.0~1.0,
    "risk_factors": [string],
    "logic_chain": [string]
}}
"""
            },
            "REVERSAL": {
                "description": "反转策略",
                "conditions": [
                    "RSI 超买/超卖",
                    "MACD 背离",
                    "成交量异常"
                ],
                "prompt_template": """
作为专业期权交易员，请分析以下反转机会：

市场数据：
- 股票: {symbol}
- 时间周期: {timeframes}
- 市场情绪: {market_sentiment}
- 波动率: {volatility}
- 板块强度: {sector_strength}

技术指标：
{technical_indicators}

成交量分析：
{volume_profile}

期权链数据：
{options_chain}

请评估：
1. 反转信号的可信度
2. 关键支撑/阻力位
3. 建议的期权策略

输出JSON格式：
{{
    "reversal_analysis": {{
        "type": "BULLISH/BEARISH",
        "strength": "STRONG/MODERATE/WEAK",
        "confirmation_signals": [string]
    }},
    "key_levels": {{
        "support": [float],
        "resistance": [float],
        "stop_loss": float
    }},
    "suggested_strategy": {{
        "type": "CALL/PUT/SPREAD",
        "strike": float,
        "expiration_days": int,
        "position_size": "SMALL/MEDIUM/LARGE",
        "risk_level": "LOW/MEDIUM/HIGH"
    }},
    "confidence": 0.0~1.0,
    "risk_factors": [string],
    "logic_chain": [string]
}}
"""
            },
            "SECTOR_DIVERGENCE": {
                "description": "板块背离策略",
                "conditions": [
                    "个股表现与所属ETF背离",
                    "相对强弱指数(RSI)差异显著",
                    "异常成交量"
                ],
                "prompt_template": """
作为专业期权交易员，请分析以下板块背离交易机会：

市场数据：
- 股票: {symbol}
- 时间周期: {timeframes}
- 市场情绪: {market_sentiment}
- 波动率: {volatility}
- 板块强度: {sector_strength}

技术指标：
{technical_indicators}

成交量分析：
{volume_profile}

ETF对比分析：
- 个股与ETF走势对比
- 相对强弱评估
- 板块内对比分析

请评估：
1. 背离的强度和可信度
2. 个股独立行情的驱动因素
3. 合适的入场点和期权策略

输出JSON格式：
{{
    "divergence_analysis": {{
        "type": "BULLISH/BEARISH",
        "strength": "STRONG/MODERATE/WEAK",
        "etf_relation": "OUTPERFORMING/UNDERPERFORMING",
        "expected_duration": "SHORT/MEDIUM/LONG"
    }},
    "catalyst_factors": [string],
    "suggested_strategy": {{
        "type": "CALL/PUT/SPREAD/IRON_CONDOR",
        "strike": float,
        "expiration_days": int,
        "position_size": "SMALL/MEDIUM/LARGE",
        "risk_level": "LOW/MEDIUM/HIGH"
    }},
    "confidence": 0.0~1.0,
    "risk_factors": [string],
    "logic_chain": [string]
}}
"""
            },
            "VOLATILITY_REVERSAL": {
                "description": "波动率反转策略",
                "conditions": [
                    "隐含波动率处于极值",
                    "期权IV百分位排名异常",
                    "期权Skew曲线异常"
                ],
                "prompt_template": """
作为专业期权交易员，请分析以下波动率反转机会：

市场数据：
- 股票: {symbol}
- 时间周期: {timeframes}
- 当前波动率: {volatility}
- IV百分位排名: {volatility_percentile}
- 历史波动率HV: {historical_volatility}

波动率指标：
- IV-HV价差: {iv_hv_spread}
- IV Skew陡峭度: {iv_skew}
- 期权链异常: {options_anomalies}

成交量分析：
{volume_profile}

请评估：
1. 波动率反转概率和预期幅度
2. 最佳策略类型(跨式/宽跨式/蝶式)
3. 最佳到期日选择

输出JSON格式：
{{
    "volatility_analysis": {{
        "current_state": "EXTREMELY_HIGH/HIGH/NORMAL/LOW/EXTREMELY_LOW",
        "reversal_probability": 0.0~1.0,
        "expected_movement": "SPIKE/GRADUAL_INCREASE/GRADUAL_DECREASE/COLLAPSE"
    }},
    "iv_factors": {{
        "term_structure": "NORMAL/INVERTED/FLAT",
        "skew_analysis": "STEEP/NORMAL/FLAT"
    }},
    "suggested_strategy": {{
        "type": "STRADDLE/STRANGLE/IRON_CONDOR/BUTTERFLY",
        "strikes": [float, float],
        "expiration_days": int,
        "position_size": "SMALL/MEDIUM/LARGE",
        "risk_level": "LOW/MEDIUM/HIGH"
    }},
    "confidence": 0.0~1.0,
    "risk_factors": [string],
    "logic_chain": [string]
}}
"""
            },
            "OPTIONS_FLOW": {
                "description": "期权流动性异常策略",
                "conditions": [
                    "期权成交量显著增加",
                    "看涨/看跌比率异常",
                    "大单交易活动"
                ],
                "prompt_template": """
作为专业期权交易员，请分析以下期权流动性异常情况：

市场数据：
- 股票: {symbol}
- 时间周期: {timeframes}
- 市场情绪: {market_sentiment}
- 波动率: {volatility}

期权流动性指标：
- 看涨/看跌比率: {call_put_ratio}
- 期权成交量变化: {options_volume_change}%
- 大单交易情况: {large_trades_summary}
- 机构持仓变化: {institutional_holdings_change}%

请评估：
1. 期权流动性异常的性质和可能原因
2. 隐含的价格走向和预期时间
3. 最优的跟随策略

输出JSON格式：
{{
    "options_flow_analysis": {{
        "bias": "BULLISH/BEARISH/NEUTRAL", 
        "unusual_activity_level": "EXTREME/HIGH/MODERATE/LOW",
        "likely_catalysts": [string],
        "smart_money_direction": "BUYING/SELLING/MIXED/UNCLEAR"
    }},
    "potential_targets": {{
        "price_targets": [float, float],
        "timeframe": "DAYS/WEEKS/MONTHS"
    }},
    "suggested_strategy": {{
        "type": "DIRECTIONAL/SPREAD/HEDGE",
        "specific_strategy": "CALL/PUT/CALL_SPREAD/PUT_SPREAD/IRON_CONDOR",
        "strike": float,
        "expiration_days": int,
        "position_size": "SMALL/MEDIUM/LARGE",
        "risk_level": "LOW/MEDIUM/HIGH"
    }},
    "confidence": 0.0~1.0,
    "risk_factors": [string],
    "logic_chain": [string]
}}
"""
            }
        }
    
    def _format_technical_indicators(self, indicators: Dict[str, float]) -> str:
        """格式化技术指标数据"""
        return "\n".join([f"- {k}: {v}" for k, v in indicators.items()])
    
    def _format_volume_profile(self, profile: Dict[str, float]) -> str:
        """格式化成交量数据"""
        return "\n".join([f"- {k}: {v}" for k, v in profile.items()])
    
    def _format_options_chain(self, chain: Dict[str, Any]) -> str:
        """格式化期权链数据"""
        return json.dumps(chain, indent=2, ensure_ascii=False)
    
    def build_prompt(self, context: StrategyPromptContext, scenario: str) -> str:
        """构建策略提示词"""
        if scenario not in self.market_scenarios:
            raise ValueError(f"Unknown scenario: {scenario}")
        
        template = self.market_scenarios[scenario]["prompt_template"]
        
        # 格式化数据
        technical_indicators = self._format_technical_indicators(context.technical_indicators)
        volume_profile = self._format_volume_profile(context.volume_profile)
        options_chain = self._format_options_chain(context.options_chain)
        
        # 填充模板
        prompt = template.format(
            symbol=context.symbol,
            timeframes=", ".join(context.timeframes),
            market_sentiment=context.market_sentiment,
            volatility=context.volatility,
            sector_strength=context.sector_strength,
            technical_indicators=technical_indicators,
            volume_profile=volume_profile,
            options_chain=options_chain
        )
        
        return prompt.strip()


# 策略名称到场景映射
STRATEGY_PRESET_MAPPING = {
    "trend_following": "TREND_FOLLOWING",
    "breakout": "BREAKOUT",
    "reversal": "REVERSAL",
    "sector_divergence": "SECTOR_DIVERGENCE",
    "volatility_reversal": "VOLATILITY_REVERSAL",
    "options_flow": "OPTIONS_FLOW"
}


def get_strategy_preset(preset_name: str) -> Optional[Dict[str, Any]]:
    """
    通过名称获取预设策略配置
    
    Args:
        preset_name: 策略名称 (例如 'trend_following', 'breakout', 等)
        
    Returns:
        包含策略参数的字典，如果策略不存在则返回None
    """
    # 初始化预设生成器
    preset_generator = PresetStrategyPrompt()
    
    # 转换策略名称为场景名称
    preset_name = preset_name.lower()
    if preset_name not in STRATEGY_PRESET_MAPPING:
        return None
        
    scenario = STRATEGY_PRESET_MAPPING[preset_name]
    
    # 获取场景配置
    if scenario not in preset_generator.market_scenarios:
        return None
        
    scenario_data = preset_generator.market_scenarios[scenario]
    
    # 创建预设配置
    preset = {
        "name": preset_name,
        "scenario": scenario,
        "description": scenario_data["description"],
        "conditions": scenario_data["conditions"],
        "prompt_template": scenario_data["prompt_template"]
    }
    
    return preset


if __name__ == "__main__":
    # 测试代码
    prompt_builder = PresetStrategyPrompt()
    
    # 示例上下文
    test_context = StrategyPromptContext(
        symbol="TSLA",
        timeframes=["1m", "5m", "15m"],
        market_sentiment="positive",
        volatility="medium",
        news_summary="特斯拉发布新产品",
        sector_strength="strong",
        technical_indicators={
            "RSI": 65.5,
            "MACD": 0.5,
            "EMA20": 148.3,
            "EMA50": 145.8
        },
        volume_profile={
            "relative_volume": 1.2,
            "volume_trend": "increasing",
            "unusual_volume": False
        },
        options_chain={},
        ask="请分析TSLA的交易策略"
    )
    
    # 测试预设策略获取
    for preset_name in ["trend_following", "breakout", "unknown_strategy"]:
        preset = get_strategy_preset(preset_name)
        if preset:
            print(f"Found preset: {preset['name']} ({preset['description']})")
        else:
            print(f"Preset not found: {preset_name}")
            
    # 测试提示词生成
    for scenario in ["TREND_FOLLOWING", "BREAKOUT"]:
        prompt = prompt_builder.build_prompt(test_context, scenario)
        print(f"\n{scenario} PROMPT:\n{'-'*40}\n{prompt[:200]}...\n") 