"""
AI智能策略生成器 v2.0
多因子融合型AI策略生成系统 - 6.0版本升级核心
"""
import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from .deepseek_api import get_deepseek_response

logger = logging.getLogger(__name__)

# 升级版多因子策略提示模板
MULTI_FACTOR_STRATEGY_TEMPLATE = """
你是一位专业的量化交易策略分析师，专注于多因子分析。请基于以下多维度市场数据，生成一个全面的交易策略：

{market_data}

基于以下因子数据:
{factor_data}

基于上述数据，请提供:

1. 市场趋势分析: 分析当前趋势方向和强度
2. 多因子综合评分(1-10): 按价格动量、资金流向、波动率、技术指标等维度给出评分
3. 因子冲突分析: 若存在相互矛盾的因子信号，说明原因及如何处理
4. 交易信号: 明确指出是买入、卖出还是持有信号，以及信号强度(1-10)
5. 建议的入场价格范围及理由
6. 止损价位(附带触发条件)
7. 目标价格(附带不同概率的多个目标)
8. 风险评级(低/中/高)与风险来源分析
9. 时间框架建议: 短线/中线/长线

请给出简明扼要的分析，重点突出实际可执行的交易策略。
"""

# 因子权重模板定义
DEFAULT_FACTOR_WEIGHTS = {
    "price_momentum": 0.20,    # 价格动量
    "volume": 0.15,            # 成交量
    "technical": 0.20,         # 技术指标
    "fund_flow": 0.15,         # 资金流
    "volatility": 0.10,        # 波动率
    "sentiment": 0.10,         # 市场情绪
    "fundamental": 0.10        # 基本面
}

class AIMultiFactorStrategy:
    """升级版多因子智能策略生成器"""
    
    def __init__(self, api_key=None, factor_weights=None, knowledge_base=None):
        """
        初始化多因子策略生成器
        
        参数:
            api_key (str): DeepSeek API密钥，默认从环境变量获取
            factor_weights (dict): 自定义因子权重，默认使用标准配置
            knowledge_base: 知识库实例，用于查询历史策略和优化建议
        """
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.factor_weights = factor_weights or DEFAULT_FACTOR_WEIGHTS
        self.knowledge_base = knowledge_base
        self.strategy_history = []
    
    def generate_strategy(self, 
                          symbol: str, 
                          price_data: pd.DataFrame, 
                          factors: Dict[str, Any], 
                          timeframe: str = "daily",
                          market_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        生成多因子交易策略
        
        参数:
            symbol (str): 股票/期权代码
            price_data (pd.DataFrame): 价格历史数据
            factors (dict): 多因子数据字典，包含各类指标
            timeframe (str): 时间周期(intraday, daily, weekly, monthly)
            market_context (dict): 可选的市场上下文信息
            
        返回:
            dict: 包含策略分析、多因子评分和交易建议的完整结果
        """
        # 1. 格式化市场数据
        market_data = self._format_market_data(symbol, price_data, timeframe, market_context)
        
        # 2. 格式化因子数据
        factor_data = self._format_factor_data(factors)
        
        # 3. 从知识库获取历史经验(如果有)
        historical_insights = self._get_historical_insights(symbol, timeframe)
        
        # 4. 构建增强型提示词
        prompt = self._build_enhanced_prompt(
            market_data=market_data,
            factor_data=factor_data,
            historical_insights=historical_insights
        )
        
        # 5. 调用API获取策略
        system_prompt = """你是一位专业的多因子量化分析师，擅长综合各类数据产生交易决策。
        你的分析必须客观、全面、精确，特别关注因子间的相互印证或冲突，并给出可执行的交易建议。"""
        
        strategy_text = get_deepseek_response(
            prompt=prompt,
            api_key=self.api_key, 
            system_prompt=system_prompt, 
            max_tokens=1500,
            temperature=0.3
        )
        
        # 6. 解析策略结果
        result = {
            "symbol": symbol,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "timeframe": timeframe,
            "strategy_text": strategy_text,
            "factors_used": list(factors.keys()),
            "raw": {
                "market_data": market_data,
                "factor_data": factor_data,
                "prompt": prompt
            }
        }
        
        # 7. 提取结构化信号
        signal = self._extract_structured_signal(strategy_text, symbol, factors)
        if signal:
            result.update(signal)
        
        # 8. 计算多因子综合评分
        factor_score = self._calculate_combined_factor_score(factors, signal)
        result["factor_score"] = factor_score
        
        # 9. 记录到历史记录
        self.strategy_history.append({
            "timestamp": result["timestamp"],
            "symbol": symbol,
            "signal": signal.get("signal_type") if signal else None,
            "factor_score": factor_score
        })
        
        return result
    
    def _format_market_data(self, symbol: str, price_data: pd.DataFrame, 
                           timeframe: str, market_context: Optional[Dict] = None) -> str:
        """格式化市场数据为文本格式"""
        # 获取最近的价格数据
        recent_data = price_data.tail(15)  # 扩展为15个周期
        latest = price_data.iloc[-1]
        
        # 基本信息
        result = f"股票代码: {symbol}\n"
        result += f"时间周期: {timeframe}\n"
        result += f"当前价格: {latest['close']:.2f}\n"
        result += f"52周最高: {price_data['high'].max():.2f}\n"
        result += f"52周最低: {price_data['low'].min():.2f}\n\n"
        
        # 计算一些基本统计量
        returns = price_data['close'].pct_change().dropna()
        result += f"近期波动率: {returns.std() * 100:.2f}%\n"
        result += f"年化收益: {returns.mean() * 252 * 100:.2f}%\n\n"
        
        # 最近价格走势
        result += "最近价格数据:\n"
        for date, row in recent_data.iterrows():
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            result += f"{date_str}: 开盘 {row['open']:.2f}, 最高 {row['high']:.2f}, 最低 {row['low']:.2f}, 收盘 {row['close']:.2f}"
            if 'volume' in row:
                result += f", 成交量 {row['volume']:,}\n"
            else:
                result += "\n"
        
        # 添加市场上下文(如有)
        if market_context:
            result += "\n市场环境:\n"
            for key, value in market_context.items():
                result += f"- {key}: {value}\n"
        
        return result
    
    def _format_factor_data(self, factors: Dict[str, Any]) -> str:
        """格式化多因子数据为文本格式"""
        result = ""
        
        # 技术指标因子
        if "technical" in factors:
            result += "\n技术指标因子:\n"
            for name, value in factors["technical"].items():
                result += f"- {name}: {value}\n"
        
        # 资金流向因子
        if "fund_flow" in factors:
            result += "\n资金流向因子:\n"
            for name, value in factors["fund_flow"].items():
                result += f"- {name}: {value}\n"
        
        # 波动率因子
        if "volatility" in factors:
            result += "\n波动率因子:\n"
            for name, value in factors["volatility"].items():
                result += f"- {name}: {value}\n"
        
        # 情绪因子
        if "sentiment" in factors:
            result += "\n市场情绪因子:\n"
            for name, value in factors["sentiment"].items():
                result += f"- {name}: {value}\n"
        
        # 基本面因子
        if "fundamental" in factors:
            result += "\n基本面因子:\n"
            for name, value in factors["fundamental"].items():
                result += f"- {name}: {value}\n"
        
        # 价格动量因子
        if "price_momentum" in factors:
            result += "\n价格动量因子:\n"
            for name, value in factors["price_momentum"].items():
                result += f"- {name}: {value}\n"
        
        # 特殊因子
        if "custom" in factors:
            result += "\n自定义因子:\n"
            for name, value in factors["custom"].items():
                result += f"- {name}: {value}\n"
        
        return result
    
    def _get_historical_insights(self, symbol: str, timeframe: str) -> Optional[str]:
        """从知识库获取历史经验和优化建议"""
        if not self.knowledge_base:
            return None
        
        try:
            # 查询知识库获取历史经验
            insights = self.knowledge_base.query_insights(
                symbol=symbol, 
                timeframe=timeframe,
                limit=3  # 获取最近3条相关经验
            )
            
            if not insights:
                return None
            
            # 格式化历史经验
            result = "\n历史经验参考:\n"
            for i, insight in enumerate(insights, 1):
                result += f"{i}. {insight['date']} - {insight['summary']}\n"
                if "lesson" in insight:
                    result += f"   经验: {insight['lesson']}\n"
            
            return result
        except Exception as e:
            logger.warning(f"获取历史经验时出错: {e}")
            return None
    
    def _build_enhanced_prompt(self, market_data: str, factor_data: str, 
                              historical_insights: Optional[str] = None) -> str:
        """构建增强型提示词"""
        prompt = MULTI_FACTOR_STRATEGY_TEMPLATE.format(
            market_data=market_data,
            factor_data=factor_data
        )
        
        # 添加历史经验
        if historical_insights:
            prompt += f"\n{historical_insights}\n"
            prompt += "请充分吸取上述历史经验，优化你的策略建议。\n"
        
        # 添加因子权重信息
        prompt += "\n因子权重参考:\n"
        for factor, weight in self.factor_weights.items():
            prompt += f"- {factor}: {weight*100:.0f}%\n"
        
        return prompt
    
    def _extract_structured_signal(self, strategy_text: str, symbol: str, 
                                  factors: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从策略文本中提取结构化的交易信号和因子分析"""
        prompt = f"""
        请分析以下交易策略文本，提取关键信息并以JSON格式返回:
        
        {strategy_text}
        
        请提取以下字段(如果存在):
        - signal_type: 信号类型，必须是以下之一: "buy", "sell", "hold"
        - confidence: 信号强度或置信度，1-10的数字
        - entry_price_low: 建议入场价格下限
        - entry_price_high: 建议入场价格上限
        - stop_loss: 止损价格
        - target_price_1: 第一目标价格(高概率)
        - target_price_2: 第二目标价格(中概率)
        - target_price_3: 第三目标价格(低概率)
        - risk_level: 风险等级，必须是以下之一: "low", "medium", "high"
        - trend: 市场趋势，必须是以下之一: "bullish", "bearish", "neutral", "ranging"
        - timeframe: 建议持仓时间，必须是以下之一: "day_trade", "short_term", "medium_term", "long_term"
        - factor_scores: 各因子评分对象，包含各个因子的评分(1-10)
        - factor_conflicts: 发现的因子冲突描述
        
        以有效的JSON格式返回结果，只返回JSON，不要有其他文本。
        如果无法从文本中提取某个字段，则将该字段设为null。
        """
        
        try:
            # 调用API提取结构化信号
            extraction_result = get_deepseek_response(
                prompt=prompt,
                api_key=self.api_key, 
                temperature=0.1,
                max_tokens=1000
            )
            
            # 尝试解析JSON
            signal = json.loads(extraction_result)
            
            # 添加股票代码
            signal["symbol"] = symbol
            
            # 添加时间戳
            signal["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 添加因子使用信息
            signal["factors_used"] = list(factors.keys())
            
            return signal
        except Exception as e:
            logger.warning(f"无法从策略文本中提取结构化信号: {e}")
            return None
    
    def _calculate_combined_factor_score(self, factors: Dict[str, Any], 
                                        signal: Optional[Dict[str, Any]]) -> float:
        """计算多因子综合评分"""
        # 如果有AI提取的因子评分，直接用它计算加权分数
        if signal and "factor_scores" in signal and signal["factor_scores"]:
            try:
                # 计算加权分数
                scores = signal["factor_scores"]
                weighted_score = 0
                total_weight = 0
                
                for factor, weight in self.factor_weights.items():
                    if factor in scores and scores[factor] is not None:
                        weighted_score += scores[factor] * weight
                        total_weight += weight
                
                # 返回归一化的分数
                if total_weight > 0:
                    return weighted_score / total_weight
                return 5.0  # 默认中性分数
            except Exception as e:
                logger.warning(f"计算因子评分时出错: {e}")
        
        # 如果没有AI评分，使用简单算法计算一个基本分数
        # 根据信号类型和置信度给出基础分数
        base_score = 5.0  # 默认中性分数
        if signal:
            # 根据信号类型调整基础分数
            if signal.get("signal_type") == "buy":
                base_score = 6.5 + (signal.get("confidence", 5) - 5) * 0.3
            elif signal.get("signal_type") == "sell":
                base_score = 3.5 - (signal.get("confidence", 5) - 5) * 0.3
            
            # 确保分数在1-10范围内
            base_score = max(1, min(10, base_score))
        
        return base_score
    
    def backtest_strategy(self, strategy_result: Dict[str, Any], 
                         price_data: pd.DataFrame) -> Dict[str, Any]:
        """
        简单回测策略(仅用于实时评估)
        
        参数:
            strategy_result: 策略生成结果
            price_data: 后续价格数据
            
        返回:
            简单回测结果
        """
        # 这个简化版回测仅作为策略评估参考
        # 完整回测应由专用回测系统实现
        if not strategy_result.get("signal_type") or len(price_data) < 5:
            return {"status": "insufficient_data"}
        
        signal = strategy_result.get("signal_type")
        entry_low = strategy_result.get("entry_price_low")
        entry_high = strategy_result.get("entry_price_high")
        stop_loss = strategy_result.get("stop_loss")
        target_1 = strategy_result.get("target_price_1")
        
        # 简单回测逻辑
        triggered = False
        stop_hit = False
        target_hit = False
        max_profit_pct = 0
        max_loss_pct = 0
        
        entry_price = None
        
        for _, bar in price_data.iterrows():
            # 检查是否触发入场
            if not triggered and entry_low and entry_high:
                if bar['low'] <= entry_high and bar['high'] >= entry_low:
                    # 假设以入场区间中点入场
                    entry_price = (entry_low + entry_high) / 2
                    triggered = True
                    continue
            
            # 已入场后检查止损和目标
            if triggered and entry_price:
                if signal == "buy":
                    # 计算当前利润百分比
                    curr_profit_pct = (bar['close'] - entry_price) / entry_price * 100
                    
                    # 更新最大利润/亏损
                    max_profit_pct = max(max_profit_pct, curr_profit_pct)
                    max_loss_pct = min(max_loss_pct, curr_profit_pct)
                    
                    # 检查止损
                    if stop_loss and bar['low'] <= stop_loss:
                        stop_hit = True
                        final_profit_pct = (stop_loss - entry_price) / entry_price * 100
                        break
                    
                    # 检查目标价
                    if target_1 and bar['high'] >= target_1:
                        target_hit = True
                        final_profit_pct = (target_1 - entry_price) / entry_price * 100
                        break
                
                elif signal == "sell":
                    # 计算当前利润百分比(做空)
                    curr_profit_pct = (entry_price - bar['close']) / entry_price * 100
                    
                    # 更新最大利润/亏损
                    max_profit_pct = max(max_profit_pct, curr_profit_pct)
                    max_loss_pct = min(max_loss_pct, curr_profit_pct)
                    
                    # 检查止损
                    if stop_loss and bar['high'] >= stop_loss:
                        stop_hit = True
                        final_profit_pct = (entry_price - stop_loss) / entry_price * 100
                        break
                    
                    # 检查目标价
                    if target_1 and bar['low'] <= target_1:
                        target_hit = True
                        final_profit_pct = (entry_price - target_1) / entry_price * 100
                        break
        
        # 如果未触发任何出场条件，计算最终结果
        if triggered and not (stop_hit or target_hit) and len(price_data) > 0:
            if signal == "buy":
                final_profit_pct = (price_data.iloc[-1]['close'] - entry_price) / entry_price * 100
            else:
                final_profit_pct = (entry_price - price_data.iloc[-1]['close']) / entry_price * 100
        else:
            final_profit_pct = 0
        
        return {
            "triggered": triggered,
            "stop_hit": stop_hit,
            "target_hit": target_hit,
            "max_profit_pct": max_profit_pct,
            "max_loss_pct": max_loss_pct,
            "final_profit_pct": final_profit_pct if triggered else None,
            "success": target_hit or (triggered and final_profit_pct > 0)
        }


# 测试代码
if __name__ == "__main__":
    # 创建示例价格数据
    dates = pd.date_range(end=datetime.now().date(), periods=30)
    prices = pd.DataFrame({
        'open': [150 + i * 0.5 + ((-1)**i) for i in range(30)],
        'high': [153 + i * 0.5 + ((-1)**i) * 2 for i in range(30)],
        'low': [148 + i * 0.5 - ((-1)**i) for i in range(30)],
        'close': [151 + i * 0.5 for i in range(30)],
        'volume': [30000000 + ((-1)**i) * 5000000 for i in range(30)]
    }, index=dates)
    
    # 创建示例多因子数据
    factors = {
        "technical": {
            "RSI(14)": 56.8,
            "MACD": 1.25,
            "Signal Line": 0.75,
            "MA(50)": 145.3,
            "MA(200)": 138.7,
            "Bollinger Bands": "上轨: 158.3, 中轨: 151.2, 下轨: 144.1",
            "Stochastic %K": 70.5,
            "Stochastic %D": 65.2
        },
        "fund_flow": {
            "institutional_buying": "moderate_inflow",
            "retail_activity": "high_buying",
            "smart_money_flow": 0.65,  # 0-1 scale
            "average_volume_ratio": 1.2  # 相对于平均成交量
        },
        "volatility": {
            "historical_vol_20d": 22.5,
            "implied_volatility": 25.8,
            "vix_current": 18.2,
            "vix_change": -1.5
        },
        "sentiment": {
            "news_sentiment": 0.75,  # -1 to 1 scale
            "social_media_score": 0.6,  # -1 to 1 scale
            "analyst_consensus": "bullish",
            "put_call_ratio": 0.85
        }
    }
    
    # 使用自定义因子权重
    custom_weights = {
        "price_momentum": 0.25,
        "volume": 0.10,
        "technical": 0.25,
        "fund_flow": 0.20,
        "volatility": 0.10,
        "sentiment": 0.10,
        "fundamental": 0.0  # 暂不使用基本面因子
    }
    
    # 测试多因子策略生成
    generator = AIMultiFactorStrategy(factor_weights=custom_weights)
    strategy = generator.generate_strategy(
        symbol="SPY", 
        price_data=prices, 
        factors=factors, 
        timeframe="daily",
        market_context={
            "overall_market": "bullish",
            "sector_performance": "technology +1.5%, healthcare -0.3%",
            "economic_events": "Fed meeting in 2 days, expected 25bp rate cut"
        }
    )
    
    print("===== 多因子交易策略 =====")
    print(strategy['strategy_text'])
    
    # 如果成功提取了结构化信号
    if 'signal_type' in strategy:
        print("\n===== 提取的交易信号 =====")
        signal_info = {k: v for k, v in strategy.items() 
                      if k not in ['strategy_text', 'raw', 'timestamp']}
        print(json.dumps(signal_info, indent=2, ensure_ascii=False)) 