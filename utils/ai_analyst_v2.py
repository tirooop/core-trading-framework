from typing import Dict, Any, Optional, List
import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from .preset_strategy_prompt import PresetStrategyPrompt, StrategyPromptContext, get_strategy_preset

class AIAnalyst:
    """增强版 AI 分析器"""
    
    def __init__(self, notifier_dispatcher=None):
        load_dotenv()
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        
        if self.api_key:
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        else:
            print("Warning: DEEPSEEK_API_KEY not found in .env file. AI analysis will be limited.")
            self.headers = {
                "Content-Type": "application/json"
            }
        
        # 初始化提示词生成器
        self.prompt_builder = PresetStrategyPrompt()
        
        # 当前使用的预设策略
        self.current_preset = None
        
        # 通知调度器
        self.notifier_dispatcher = notifier_dispatcher
        
        # 定义分析结果的数据结构
        self.analysis_result = {
            "timestamp": "",
            "symbol": "",
            "market_analysis": {},
            "strategy_analysis": {},
            "risk_assessment": {},
            "llm_analysis": {}
        }
    
    def set_strategy_preset(self, preset_name: str):
        """设置预设策略配置"""
        preset = get_strategy_preset(preset_name)
        if preset:
            self.current_preset = preset
            print(f"Set strategy preset: {preset.get('name')} - {preset.get('description')}")
            return True
        else:
            print(f"Strategy preset '{preset_name}' not found")
            return False
    
    def _call_deepseek_api(self, prompt: str) -> Optional[Dict[str, Any]]:
        """调用 DeepSeek API"""
        try:
            # Check if API key is available
            if not self.api_key:
                print("DeepSeek API key not available. Returning mock analysis.")
                # Return a mock response for testing
                return {
                    "action": "Hold",
                    "confidence": 0.5,
                    "risk_level": "MEDIUM",
                    "explanation": "API key not available. This is a mock response.",
                    "suggested_strategy": {
                        "entry_price": 0,
                        "target_price": 0,
                        "stop_loss": 0,
                        "position_size": "SMALL"
                    },
                    "risk_factors": ["API key not available"]
                }
                
            payload = {
                "model": "deepseek-ai/DeepSeek-V3",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # 解析返回的 JSON 字符串
            return json.loads(content)
            
        except Exception as e:
            print(f"Error calling DeepSeek API: {str(e)}")
            return None
    
    def _determine_market_scenario(self, context: StrategyPromptContext) -> str:
        """根据市场数据确定最适合的策略场景"""
        # 如果已设置预设策略，则使用该策略
        if self.current_preset and 'scenario' in self.current_preset:
            return self.current_preset['scenario']
            
        # 否则根据市场数据确定策略
        if context.technical_indicators.get("RSI", 50) > 65:
            return "BREAKOUT"
        elif context.technical_indicators.get("RSI", 50) < 35:
            return "REVERSAL"
        else:
            return "TREND_FOLLOWING"
    
    def analyze_market(self, context: StrategyPromptContext) -> Optional[Dict[str, Any]]:
        """分析市场数据"""
        try:
            # 确定市场场景
            scenario = self._determine_market_scenario(context)
            
            # 构建提示词
            prompt = self.prompt_builder.build_prompt(context, scenario)
            
            # 调用 API
            analysis_result = self._call_deepseek_api(prompt)
            
            if analysis_result:
                # 更新分析结果
                self.analysis_result = {
                    "timestamp": datetime.now().isoformat(),
                    "symbol": context.symbol,
                    "market_analysis": {
                        "scenario": scenario,
                        "market_sentiment": context.market_sentiment,
                        "volatility": context.volatility,
                        "sector_strength": context.sector_strength
                    },
                    "strategy_analysis": analysis_result.get("suggested_strategy", {}),
                    "risk_assessment": {
                        "risk_factors": analysis_result.get("risk_factors", []),
                        "confidence": analysis_result.get("confidence", 0)
                    },
                    "llm_analysis": analysis_result
                }
                
                # 如果有通知调度器，则发送通知
                if self.notifier_dispatcher:
                    self.notifier_dispatcher.dispatch_ai_insight(self.analysis_result)
                
                return self.analysis_result
            
            return None
            
        except Exception as e:
            print(f"Error in market analysis: {str(e)}")
            return None
    
    def analyze_multiple_timeframes(self, context: StrategyPromptContext) -> Optional[Dict[str, Any]]:
        """分析多个时间周期"""
        try:
            results = {}
            
            # 对每个时间周期进行分析
            for timeframe in context.timeframes:
                # 更新上下文中的时间周期
                timeframe_context = StrategyPromptContext(
                    symbol=context.symbol,
                    timeframes=[timeframe],
                    market_sentiment=context.market_sentiment,
                    volatility=context.volatility,
                    news_summary=context.news_summary,
                    sector_strength=context.sector_strength,
                    technical_indicators=context.technical_indicators,
                    volume_profile=context.volume_profile,
                    options_chain=context.options_chain,
                    ask=context.ask
                )
                
                # 分析当前时间周期
                result = self.analyze_market(timeframe_context)
                if result:
                    results[timeframe] = result
            
            if results:
                # 合并多个时间周期的分析结果
                merged_analysis = self._merge_timeframe_analysis(results)
                
                # 如有通知调度器，发送合并的分析结果
                if self.notifier_dispatcher and merged_analysis.get("consensus", {}).get("confidence", 0) >= 0.6:
                    self._send_consensus_analysis(merged_analysis)
                    
                return merged_analysis
            
            return None
            
        except Exception as e:
            print(f"Error in multiple timeframe analysis: {str(e)}")
            return None
    
    def analyze(self, symbol: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """分析单一股票市场数据，适配 StrategyExecutor"""
        try:
            # 从市场数据创建分析上下文
            context = self._create_context_from_market_data(symbol, market_data)
            
            # 分析市场数据
            return self.analyze_market(context)
            
        except Exception as e:
            print(f"Error analyzing market data: {str(e)}")
            return None
    
    def _create_context_from_market_data(self, symbol: str, data: Dict[str, Any]) -> StrategyPromptContext:
        """从市场数据创建分析上下文"""
        # 提取技术指标
        technical_indicators = {}
        if isinstance(data, dict):
            for key in ['RSI', 'MACD', 'BB_Upper', 'BB_Lower', 'SMA_20', 'SMA_50', 'SMA_200', 'Volatility']:
                if key in data:
                    technical_indicators[key] = float(data[key])
        elif hasattr(data, 'iloc') and len(data) > 0:
            # pandas DataFrame
            last_row = data.iloc[-1]
            for col in data.columns:
                if col in ['RSI', 'MACD', 'BB_Upper', 'BB_Lower', 'SMA_20', 'SMA_50', 'SMA_200', 'Volatility']:
                    technical_indicators[col] = float(last_row[col])
        
        # 提取成交量数据
        volume_profile = {
            "relative_volume": 1.0,
            "volume_trend": "stable",
            "unusual_volume": False
        }
        
        if isinstance(data, dict) and 'Volume' in data:
            volume_profile["relative_volume"] = float(data['Volume']) / data.get('Volume_SMA20', 1.0)
        elif hasattr(data, 'iloc') and 'Volume' in data.columns:
            if 'Volume_SMA20' in data.columns:
                volume_profile["relative_volume"] = float(data.iloc[-1]['Volume']) / data.iloc[-1]['Volume_SMA20']
        
        # 创建上下文
        context = StrategyPromptContext(
            symbol=symbol,
            timeframes=["1d"],  # 默认日线
            market_sentiment="neutral",  # 默认中性
            volatility="medium",  # 默认中等波动率
            news_summary="",  # 默认无新闻
            sector_strength="0.5",  # 默认中性
            technical_indicators=technical_indicators,
            volume_profile=volume_profile,
            options_chain={},  # 默认无期权链数据
            ask="请分析市场状况，判断是否存在入场机会，给出策略建议与置信度。"
        )
        
        return context
    
    def _merge_timeframe_analysis(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """合并多个时间周期的分析结果"""
        try:
            # 初始化合并结果
            merged = {
                "timestamp": datetime.now().isoformat(),
                "symbol": next(iter(results.values())).get("symbol", "Unknown"),
                "timeframe_analysis": results,
                "consensus": {
                    "bias": self._get_consensus_bias(results),
                    "confidence": self._get_consensus_confidence(results),
                    "strategy": self._get_consensus_strategy(results)
                }
            }
            
            return merged
            
        except Exception as e:
            print(f"Error merging timeframe analysis: {str(e)}")
            return None
    
    def _get_consensus_bias(self, results: Dict[str, Dict[str, Any]]) -> str:
        """获取多个时间周期的市场偏向共识"""
        biases = []
        for result in results.values():
            if "llm_analysis" in result:
                analysis = result["llm_analysis"]
                if "trend_analysis" in analysis:
                    biases.append(analysis["trend_analysis"].get("strength", "NEUTRAL"))
                elif "breakout_analysis" in analysis:
                    biases.append(analysis["breakout_analysis"].get("type", "NEUTRAL"))
                elif "reversal_analysis" in analysis:
                    biases.append(analysis["reversal_analysis"].get("type", "NEUTRAL"))
        
        # 返回最常见的偏向
        return max(set(biases), key=biases.count) if biases else "NEUTRAL"
    
    def _get_consensus_confidence(self, results: Dict[str, Dict[str, Any]]) -> float:
        """获取多个时间周期的置信度共识"""
        confidences = []
        for result in results.values():
            if "risk_assessment" in result:
                confidences.append(result["risk_assessment"].get("confidence", 0))
        
        # 返回平均置信度
        return sum(confidences) / len(confidences) if confidences else 0
    
    def _get_consensus_strategy(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """获取多个时间周期的策略共识"""
        strategies = []
        for result in results.values():
            if "strategy_analysis" in result:
                strategies.append(result["strategy_analysis"])
        
        # 返回最保守的策略
        if strategies:
            return min(strategies, key=lambda x: x.get("risk_level", "HIGH"))
        return {}
    
    def _send_consensus_analysis(self, merged_analysis: Dict[str, Any]) -> None:
        """发送多时间周期分析共识结果"""
        if not self.notifier_dispatcher:
            return
        
        symbol = merged_analysis.get("symbol", "Unknown")
        consensus = merged_analysis.get("consensus", {})
        bias = consensus.get("bias", "NEUTRAL")
        confidence = consensus.get("confidence", 0)
        strategy = consensus.get("strategy", {})
        
        # 构建信号数据
        signal_data = {
            "type": "multi_timeframe_analysis",
            "symbol": symbol,
            "strategy": strategy.get("type", "Unknown"),
            "direction": "BULLISH" if bias in ["STRONG", "BULLISH"] else "BEARISH" if bias in ["WEAK", "BEARISH"] else "NEUTRAL",
            "confidence": confidence,
            "price": 0,  # 需要从其他地方获取当前价格
            "ai_insight": self._extract_consensus_insight(merged_analysis),
            "rr_ratio": self._calculate_risk_reward_ratio(strategy),
        }
        
        # 发送通知
        self.notifier_dispatcher.dispatch_signal(signal_data)
    
    def _extract_consensus_insight(self, merged_analysis: Dict[str, Any]) -> str:
        """从合并分析中提取核心见解"""
        timeframes = merged_analysis.get("timeframe_analysis", {})
        insights = []
        
        # 从不同时间周期中提取关键见解
        for timeframe, analysis in timeframes.items():
            if "llm_analysis" in analysis and "logic_chain" in analysis["llm_analysis"]:
                logic_chain = analysis["llm_analysis"]["logic_chain"]
                if logic_chain and len(logic_chain) > 0:
                    insights.append(f"[{timeframe}] {logic_chain[0]}")
        
        return "\n".join(insights)
    
    def _calculate_risk_reward_ratio(self, strategy: Dict[str, Any]) -> float:
        """计算风险收益比"""
        # 简单实现，实际应用中需要更复杂的计算
        if "position_size" in strategy and "risk_level" in strategy:
            position_size_map = {"SMALL": 1, "MEDIUM": 2, "LARGE": 3}
            risk_level_map = {"LOW": 3, "MEDIUM": 2, "HIGH": 1}
            
            position_size = position_size_map.get(strategy.get("position_size", "MEDIUM"), 2)
            risk_level = risk_level_map.get(strategy.get("risk_level", "MEDIUM"), 2)
            
            return position_size * risk_level / 2
        
        return 1.0  # 默认值

if __name__ == "__main__":
    # 测试代码
    analyst = AIAnalyst()
    
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
        options_chain={
            "calls": {
                "150": {"volume": 1000, "oi": 5000},
                "155": {"volume": 800, "oi": 4000}
            },
            "puts": {
                "145": {"volume": 900, "oi": 4500},
                "140": {"volume": 700, "oi": 3500}
            }
        },
        ask="请判断是否存在高置信度入场机会，并给出策略建议，风险说明与置信度。"
    )
    
    # 测试预设策略设置
    from .preset_strategy_prompt import get_strategy_preset
    preset = get_strategy_preset("breakout")
    if preset:
        analyst.set_strategy_preset(preset)
    
    # 运行分析
    result = analyst.analyze_multiple_timeframes(test_context)
    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False)) 