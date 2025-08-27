"""
AI反馈闭环模块 - 构建交易系统的自我学习和优化能力
AI量化系统6.0 - 自动学习与改进的核心组件
"""
import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple

# 导入其他模块
from utils.trade_memory_core import TradeMemory
from utils.trade_memory_analysis import TradeAnalyzer
from utils.market_data import get_default_spy_manager

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ai_feedback_loop")

class AIFeedbackLoop:
    """
    AI反馈闭环 - 分析交易结果并生成改进的策略
    """
    
    def __init__(self, 
                memory_dir: str = "data/trade_memory",
                feedback_dir: str = "data/ai_feedback",
                symbol: str = "SPY"):
        """
        初始化AI反馈闭环
        
        参数:
            memory_dir: 交易记忆目录
            feedback_dir: AI反馈存储目录
            symbol: 交易标的
        """
        self.memory_dir = memory_dir
        self.feedback_dir = feedback_dir
        self.symbol = symbol
        
        # 创建目录
        os.makedirs(feedback_dir, exist_ok=True)
        os.makedirs(os.path.join(feedback_dir, "strategies"), exist_ok=True)
        os.makedirs(os.path.join(feedback_dir, "prompts"), exist_ok=True)
        
        # 初始化交易记忆
        self.trade_memory = TradeMemory(memory_dir, symbol)
        
        # 初始化分析器
        self.analyzer = TradeAnalyzer(memory_dir, symbol, self.trade_memory.trades)
        
        # 获取市场数据
        self.market_data = get_default_spy_manager()
        
        # 加载之前生成的反馈和策略
        self.feedbacks = self._load_feedbacks()
        self.strategies = self._load_strategies()
        
        logger.info(f"AI反馈闭环已初始化，加载 {len(self.feedbacks)} 条反馈记录和 {len(self.strategies)} 个生成策略")
    
    def _load_feedbacks(self) -> List[Dict]:
        """加载反馈记录"""
        feedback_file = os.path.join(self.feedback_dir, f"{self.symbol}_feedbacks.json")
        if not os.path.exists(feedback_file):
            return []
        
        try:
            with open(feedback_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载反馈记录失败: {e}")
            return []
    
    def _save_feedbacks(self):
        """保存反馈记录"""
        feedback_file = os.path.join(self.feedback_dir, f"{self.symbol}_feedbacks.json")
        try:
            with open(feedback_file, "w") as f:
                json.dump(self.feedbacks, f, indent=2)
            logger.info(f"已保存 {len(self.feedbacks)} 条反馈记录")
        except Exception as e:
            logger.error(f"保存反馈记录失败: {e}")
    
    def _load_strategies(self) -> List[Dict]:
        """加载生成的策略"""
        strategy_file = os.path.join(self.feedback_dir, f"{self.symbol}_strategies.json")
        if not os.path.exists(strategy_file):
            return []
        
        try:
            with open(strategy_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载策略记录失败: {e}")
            return []
    
    def _save_strategies(self):
        """保存生成的策略"""
        strategy_file = os.path.join(self.feedback_dir, f"{self.symbol}_strategies.json")
        try:
            with open(strategy_file, "w") as f:
                json.dump(self.strategies, f, indent=2)
            logger.info(f"已保存 {len(self.strategies)} 个生成策略")
        except Exception as e:
            logger.error(f"保存策略记录失败: {e}")
    
    def generate_feedback(self, 
                         time_period: str = "1mo",
                         n_failures: int = 3,
                         min_trades: int = 10) -> Dict:
        """
        根据交易历史生成反馈报告
        
        参数:
            time_period: 时间范围 ("1mo", "3mo", "6mo", "1y", "all")
            n_failures: 分析的失败案例数量
            min_trades: 生成反馈所需的最少交易数量
            
        返回:
            反馈报告字典
        """
        # 确定日期范围
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = None
        
        if time_period == "1mo":
            start_date = (datetime.now() - pd.DateOffset(months=1)).strftime("%Y-%m-%d")
        elif time_period == "3mo":
            start_date = (datetime.now() - pd.DateOffset(months=3)).strftime("%Y-%m-%d")
        elif time_period == "6mo":
            start_date = (datetime.now() - pd.DateOffset(months=6)).strftime("%Y-%m-%d")
        elif time_period == "1y":
            start_date = (datetime.now() - pd.DateOffset(years=1)).strftime("%Y-%m-%d")
        
        # 获取交易数据
        trades = self.trade_memory.get_trades(start_date=start_date, end_date=end_date, limit=1000)
        
        # 检查交易数量
        if len(trades) < min_trades:
            logger.warning(f"交易数量不足，需要至少 {min_trades} 笔交易，当前仅有 {len(trades)} 笔")
            return {"error": "交易数量不足", "trades_count": len(trades), "required": min_trades}
        
        # 计算整体统计
        stats = self.trade_memory.get_stats(start_date=start_date, end_date=end_date)
        
        # 获取失败案例
        failure_trades = [t for t in trades if t.get("pnl", 0) < 0]
        failure_trades = sorted(failure_trades, key=lambda x: x.get("pnl", 0))[:n_failures]
        
        # 分析最常见的失败模式
        failure_patterns = self.analyzer.get_most_common_patterns(pattern_type="failure", limit=3)
        
        # 创建反馈报告
        feedback = {
            "timestamp": datetime.now().isoformat(),
            "time_period": time_period,
            "start_date": start_date,
            "end_date": end_date,
            "trades_count": len(trades),
            "stats": stats,
            "failure_cases": failure_trades,
            "failure_patterns": failure_patterns,
            "suggestions": []
        }
        
        # 生成改进建议
        current_price = self.market_data.get_spy_price()
        
        # 基于失败模式提出建议
        for pattern in failure_patterns:
            pattern_type = pattern.get("pattern_type")
            pattern_value = pattern.get("value")
            
            if pattern_type == "market_condition":
                suggestion = {
                    "type": "market_condition",
                    "pattern": pattern_value,
                    "description": f"避免在'{pattern_value}'市场条件下交易，或者调整策略",
                    "action": f"在识别到'{pattern_value}'时，增加止损限制或减少仓位"
                }
                feedback["suggestions"].append(suggestion)
                
            elif pattern_type == "entry_reason":
                suggestion = {
                    "type": "entry_reason",
                    "pattern": pattern_value,
                    "description": f"基于'{pattern_value}'的入场决策表现不佳",
                    "action": f"重新评估'{pattern_value}'入场信号，考虑增加额外确认因素"
                }
                feedback["suggestions"].append(suggestion)
                
            elif pattern_type == "exit_reason":
                suggestion = {
                    "type": "exit_reason",
                    "pattern": pattern_value,
                    "description": f"基于'{pattern_value}'的出场时机不理想",
                    "action": f"调整'{pattern_value}'出场规则，可能需要更早出场"
                }
                feedback["suggestions"].append(suggestion)
        
        # 添加一般性建议
        if stats["win_rate"] < 0.4:
            suggestion = {
                "type": "general",
                "pattern": "low_win_rate",
                "description": f"整体胜率较低 ({stats['win_rate']:.1%})",
                "action": "考虑提高入场标准，或者改进止损策略"
            }
            feedback["suggestions"].append(suggestion)
            
        if stats["profit_factor"] < 1.0:
            suggestion = {
                "type": "general",
                "pattern": "low_profit_factor",
                "description": f"盈亏比不理想 ({stats['profit_factor']:.2f})",
                "action": "延长盈利交易持有时间，缩短亏损交易持有时间"
            }
            feedback["suggestions"].append(suggestion)
        
        # 保存反馈
        self.feedbacks.append(feedback)
        self._save_feedbacks()
        
        return feedback
    
    def generate_improved_strategy(self, 
                                 feedback_id: Optional[int] = None) -> Dict:
        """
        基于反馈生成改进的策略
        
        参数:
            feedback_id: 反馈ID，为None时使用最新的反馈
            
        返回:
            生成的策略字典
        """
        # 获取指定反馈或最新反馈
        if feedback_id is not None and 0 <= feedback_id < len(self.feedbacks):
            feedback = self.feedbacks[feedback_id]
        elif self.feedbacks:
            feedback = self.feedbacks[-1]  # 使用最新反馈
        else:
            # 如果没有反馈，先生成一个
            feedback = self.generate_feedback()
            if "error" in feedback:
                return {"error": "无法生成反馈", "details": feedback["error"]}
        
        # 创建策略模板
        strategy = {
            "timestamp": datetime.now().isoformat(),
            "name": f"AI_Optimized_Strategy_{len(self.strategies) + 1}",
            "base_feedback_id": self.feedbacks.index(feedback) if feedback in self.feedbacks else None,
            "description": "基于交易历史和失败模式分析优化的策略",
            "rules": {
                "entry": [],
                "exit": [],
                "position_sizing": [],
                "risk_management": []
            },
            "backtest_results": None
        }
        
        # 添加入场规则
        avoided_conditions = []
        for suggestion in feedback.get("suggestions", []):
            if suggestion["type"] == "market_condition":
                avoided_conditions.append(suggestion["pattern"])
                entry_rule = {
                    "type": "market_condition_filter",
                    "description": f"避免在{suggestion['pattern']}市场条件下入场",
                    "implementation": f"if market_condition == '{suggestion['pattern']}': return False"
                }
                strategy["rules"]["entry"].append(entry_rule)
                
            elif suggestion["type"] == "entry_reason":
                entry_rule = {
                    "type": "entry_signal_enhancement",
                    "description": f"增强{suggestion['pattern']}入场信号的确认条件",
                    "implementation": f"if entry_reason == '{suggestion['pattern']}': require_additional_confirmation()"
                }
                strategy["rules"]["entry"].append(entry_rule)
        
        # 添加出场规则
        for suggestion in feedback.get("suggestions", []):
            if suggestion["type"] == "exit_reason":
                exit_rule = {
                    "type": "exit_timing_adjustment",
                    "description": f"调整{suggestion['pattern']}出场时机",
                    "implementation": f"if exit_reason == '{suggestion['pattern']}': exit_earlier()"
                }
                strategy["rules"]["exit"].append(exit_rule)
        
        # 添加仓位管理规则
        stats = feedback.get("stats", {})
        win_rate = stats.get("win_rate", 0.5)
        
        if win_rate < 0.4:
            position_rule = {
                "type": "conservative_sizing",
                "description": "由于胜率较低，采用更保守的仓位",
                "implementation": "position_size = calculate_base_size() * 0.7"
            }
            strategy["rules"]["position_sizing"].append(position_rule)
        elif win_rate > 0.6:
            position_rule = {
                "type": "aggressive_sizing",
                "description": "由于胜率较高，可以适当增加仓位",
                "implementation": "position_size = calculate_base_size() * 1.2"
            }
            strategy["rules"]["position_sizing"].append(position_rule)
        
        # 添加风险管理规则
        profit_factor = stats.get("profit_factor", 1.0)
        
        if profit_factor < 1.0:
            risk_rule = {
                "type": "tighter_stop_loss",
                "description": "设置更严格的止损以改善盈亏比",
                "implementation": "stop_loss = entry_price * 0.985  # 收紧至1.5%止损"
            }
            strategy["rules"]["risk_management"].append(risk_rule)
            
            risk_rule = {
                "type": "wider_profit_target",
                "description": "扩大目标利润以改善盈亏比",
                "implementation": "profit_target = entry_price * 1.03  # 扩大至3%目标"
            }
            strategy["rules"]["risk_management"].append(risk_rule)
        
        # 保存策略
        self.strategies.append(strategy)
        self._save_strategies()
        
        return strategy
    
    def generate_strategy_prompt(self, strategy_id: Optional[int] = None) -> str:
        """
        将策略转换为提示词格式，用于AI交易决策
        
        参数:
            strategy_id: 策略ID，为None时使用最新的策略
            
        返回:
            策略提示词
        """
        # 获取指定策略或最新策略
        if strategy_id is not None and 0 <= strategy_id < len(self.strategies):
            strategy = self.strategies[strategy_id]
        elif self.strategies:
            strategy = self.strategies[-1]  # 使用最新策略
        else:
            # 如果没有策略，先生成一个
            strategy = self.generate_improved_strategy()
            if "error" in strategy:
                return f"错误：{strategy['error']}"
        
        # 获取历史交易上下文
        historical_context = self.analyzer.generate_historical_prompt_context(
            trade_type="option",
            stats=self.trade_memory.get_stats()
        )
        
        # 市场状态信息
        current_price = self.market_data.get_spy_price()
        
        # 构建提示词
        prompt = f"""# SPY期权交易AI决策系统

## 当前市场信息
- SPY当前价格: ${current_price}
- 日期时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 策略: {strategy['name']}
{strategy['description']}

### 入场规则
"""
        
        # 添加入场规则
        for rule in strategy["rules"]["entry"]:
            prompt += f"- {rule['description']}\n"
        
        prompt += "\n### 出场规则\n"
        
        # 添加出场规则
        for rule in strategy["rules"]["exit"]:
            prompt += f"- {rule['description']}\n"
        
        prompt += "\n### 仓位管理\n"
        
        # 添加仓位管理规则
        for rule in strategy["rules"]["position_sizing"]:
            prompt += f"- {rule['description']}\n"
        
        prompt += "\n### 风险管理\n"
        
        # 添加风险管理规则
        for rule in strategy["rules"]["risk_management"]:
            prompt += f"- {rule['description']}\n"
        
        # 添加历史交易经验
        prompt += f"\n{historical_context}\n"
        
        # 添加请求
        prompt += """
## 交易决策请求
请根据当前市场情况、历史交易经验和优化策略，提供SPY期权交易建议。
包括:
1. 是否应该开仓(多/空)或保持观望
2. 如果开仓，推荐的期权合约(到期日、行权价、类型)
3. 建议的入场价格
4. 止损和目标价位
5. 决策的置信度和理由

感谢您的分析!
"""
        
        # 保存提示词
        prompt_file = os.path.join(self.feedback_dir, "prompts", 
                                 f"{strategy['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        try:
            with open(prompt_file, "w") as f:
                f.write(prompt)
            logger.info(f"已保存策略提示词到 {prompt_file}")
        except Exception as e:
            logger.error(f"保存策略提示词失败: {e}")
        
        return prompt

# 测试代码
if __name__ == "__main__":
    # 创建反馈闭环实例
    feedback_loop = AIFeedbackLoop()
    
    # 添加一些测试交易记录(如果没有的话)
    if len(feedback_loop.trade_memory.trades) < 5:
        print("添加测试交易记录...")
        
        test_trades = [
            {
                "symbol": "SPY",
                "entry_time": "2023-01-05T10:30:00",
                "exit_time": "2023-01-05T14:45:00",
                "entry_price": 380.50,
                "exit_price": 383.75,
                "direction": "LONG",
                "quantity": 100,
                "pnl": 325.0,
                "pnl_percent": 0.0085,
                "entry_reason": "突破上升趋势线",
                "exit_reason": "达到目标价",
                "market_condition": "上升趋势",
                "ai_signal": "买入",
                "ai_confidence": 0.85,
                "strategy_name": "趋势跟踪",
                "tags": ["突破", "强势"]
            },
            {
                "symbol": "SPY",
                "entry_time": "2023-01-10T09:45:00",
                "exit_time": "2023-01-10T15:30:00",
                "entry_price": 385.25,
                "exit_price": 382.40,
                "direction": "LONG",
                "quantity": 100,
                "pnl": -285.0,
                "pnl_percent": -0.0074,
                "entry_reason": "RSI超卖反弹",
                "exit_reason": "突破支撑位",
                "market_condition": "区间震荡",
                "ai_signal": "买入",
                "ai_confidence": 0.65,
                "strategy_name": "反转交易",
                "tags": ["超卖", "反弹"]
            },
            {
                "symbol": "SPY",
                "entry_time": "2023-01-15T11:15:00",
                "exit_time": "2023-01-15T16:00:00",
                "entry_price": 390.75,
                "exit_price": 388.20,
                "direction": "SHORT",
                "quantity": 100,
                "pnl": 255.0,
                "pnl_percent": 0.0065,
                "entry_reason": "顶部形态确认",
                "exit_reason": "达到目标价",
                "market_condition": "顶部形成",
                "ai_signal": "卖出",
                "ai_confidence": 0.78,
                "strategy_name": "顶部反转",
                "tags": ["顶部", "反转"]
            }
        ]
        
        for trade in test_trades:
            feedback_loop.trade_memory.add_trade(trade)
    
    # 生成反馈
    print("\n===== 生成交易反馈 =====")
    feedback = feedback_loop.generate_feedback(min_trades=3)  # 降低最小交易要求以便测试
    
    print(f"生成反馈时间: {feedback.get('timestamp')}")
    print(f"分析交易数量: {feedback.get('trades_count')}")
    
    print("\n改进建议:")
    for i, suggestion in enumerate(feedback.get("suggestions", []), 1):
        print(f"{i}. {suggestion['description']}")
        print(f"   行动: {suggestion['action']}")
    
    # 生成改进策略
    print("\n===== 生成改进策略 =====")
    strategy = feedback_loop.generate_improved_strategy()
    
    print(f"策略名称: {strategy.get('name')}")
    print(f"策略描述: {strategy.get('description')}")
    
    print("\n入场规则:")
    for rule in strategy["rules"]["entry"]:
        print(f"- {rule['description']}")
    
    print("\n出场规则:")
    for rule in strategy["rules"]["exit"]:
        print(f"- {rule['description']}")
    
    # 生成策略提示词
    print("\n===== 生成策略提示词 =====")
    prompt = feedback_loop.generate_strategy_prompt()
    
    print("提示词片段:")
    print("\n".join(prompt.split("\n")[:10]) + "\n...")
    print(f"完整提示词长度: {len(prompt)} 字符") 