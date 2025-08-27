"""
交易记忆库分析模块 - 交易模式识别与分析功能
AI量化系统6.0 - 交易记忆与自学习闭环的分析组件
"""
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import Dict, List, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("trade_memory_analysis")

class TradeAnalyzer:
    """交易分析器 - 分析交易模式和生成历史经验上下文"""
    
    def __init__(self, memory_dir: str, symbol: str, trades: List[Dict]):
        """
        初始化交易分析器
        
        参数:
            memory_dir: 记忆库存储目录
            symbol: 交易标的代码
            trades: 交易记录列表
        """
        self.memory_dir = memory_dir
        self.symbol = symbol
        self.trades = trades
    
    def analyze_trade_patterns(self, 
                              pattern_type: str = "failure", 
                              min_occurrences: int = 3) -> List[Dict]:
        """
        分析交易模式
        
        参数:
            pattern_type: 模式类型 ("failure", "success", "all")
            min_occurrences: 最小出现次数
            
        返回:
            识别的模式列表
        """
        # 根据模式类型筛选交易
        if pattern_type == "failure":
            target_trades = [t for t in self.trades if t.get("pnl", 0) < 0]
        elif pattern_type == "success":
            target_trades = [t for t in self.trades if t.get("pnl", 0) > 0]
        else:
            target_trades = self.trades
        
        # 如果交易太少，无法分析
        if len(target_trades) < min_occurrences:
            logger.warning(f"交易数量不足，无法分析模式 (当前: {len(target_trades)}, 需要: {min_occurrences})")
            return []
        
        # 提取关键特征
        patterns = []
        
        # 1. 分析市场条件
        market_conditions = {}
        for trade in target_trades:
            condition = trade.get("market_condition", "unknown")
            if condition in market_conditions:
                market_conditions[condition].append(trade)
            else:
                market_conditions[condition] = [trade]
        
        # 找出频繁的市场条件
        for condition, trades in market_conditions.items():
            if len(trades) >= min_occurrences:
                avg_pnl = np.mean([t.get("pnl", 0) for t in trades])
                patterns.append({
                    "pattern_type": "market_condition",
                    "value": condition,
                    "occurrences": len(trades),
                    "avg_pnl": avg_pnl,
                    "trades": [t.get("trade_id") for t in trades]
                })
        
        # 2. 分析入场原因
        entry_reasons = {}
        for trade in target_trades:
            reason = trade.get("entry_reason", "unknown")
            if reason in entry_reasons:
                entry_reasons[reason].append(trade)
            else:
                entry_reasons[reason] = [trade]
        
        # 找出频繁的入场原因
        for reason, trades in entry_reasons.items():
            if len(trades) >= min_occurrences:
                avg_pnl = np.mean([t.get("pnl", 0) for t in trades])
                patterns.append({
                    "pattern_type": "entry_reason",
                    "value": reason,
                    "occurrences": len(trades),
                    "avg_pnl": avg_pnl,
                    "trades": [t.get("trade_id") for t in trades]
                })
        
        # 3. 分析出场原因
        exit_reasons = {}
        for trade in target_trades:
            reason = trade.get("exit_reason", "unknown")
            if reason in exit_reasons:
                exit_reasons[reason].append(trade)
            else:
                exit_reasons[reason] = [trade]
        
        # 找出频繁的出场原因
        for reason, trades in exit_reasons.items():
            if len(trades) >= min_occurrences:
                avg_pnl = np.mean([t.get("pnl", 0) for t in trades])
                patterns.append({
                    "pattern_type": "exit_reason",
                    "value": reason,
                    "occurrences": len(trades),
                    "avg_pnl": avg_pnl,
                    "trades": [t.get("trade_id") for t in trades]
                })
        
        # 4. 分析AI建议
        ai_signals = {}
        for trade in target_trades:
            signal = trade.get("ai_signal", "unknown")
            if signal in ai_signals:
                ai_signals[signal].append(trade)
            else:
                ai_signals[signal] = [trade]
        
        # 找出频繁的AI信号
        for signal, trades in ai_signals.items():
            if len(trades) >= min_occurrences:
                avg_pnl = np.mean([t.get("pnl", 0) for t in trades])
                avg_confidence = np.mean([t.get("ai_confidence", 0) for t in trades])
                patterns.append({
                    "pattern_type": "ai_signal",
                    "value": signal,
                    "occurrences": len(trades),
                    "avg_pnl": avg_pnl,
                    "avg_confidence": avg_confidence,
                    "trades": [t.get("trade_id") for t in trades]
                })
        
        # 按出现次数排序
        patterns.sort(key=lambda x: x["occurrences"], reverse=True)
        
        # 保存模式分析
        pattern_file = os.path.join(self.memory_dir, "patterns", 
                                    f"{self.symbol}_{pattern_type}_patterns.json")
        try:
            with open(pattern_file, "w") as f:
                json.dump(patterns, f, indent=2)
            logger.info(f"已保存 {len(patterns)} 个{pattern_type}模式分析结果")
        except Exception as e:
            logger.error(f"保存模式分析结果失败: {e}")
        
        return patterns
    
    def get_most_common_patterns(self, 
                                pattern_type: str = "failure", 
                                limit: int = 5) -> List[Dict]:
        """
        获取最常见的交易模式
        
        参数:
            pattern_type: 模式类型 ("failure", "success", "all")
            limit: 最大返回数量
            
        返回:
            最常见的模式列表
        """
        pattern_file = os.path.join(self.memory_dir, "patterns", 
                                   f"{self.symbol}_{pattern_type}_patterns.json")
        if not os.path.exists(pattern_file):
            # 如果文件不存在，尝试分析
            patterns = self.analyze_trade_patterns(pattern_type=pattern_type)
        else:
            # 加载现有分析结果
            try:
                with open(pattern_file, "r") as f:
                    patterns = json.load(f)
            except Exception as e:
                logger.error(f"加载模式分析结果失败: {e}")
                patterns = []
        
        # 按出现次数排序，返回前N个
        patterns.sort(key=lambda x: x["occurrences"], reverse=True)
        return patterns[:limit]
    
    def generate_historical_prompt_context(self, 
                                         trade_type: str = "option",
                                         stats: Dict = None) -> str:
        """
        生成包含历史交易经验的提示词上下文
        用于AI交易建议生成的历史经验注入
        
        参数:
            trade_type: 交易类型 ("option", "stock", "futures")
            stats: 交易统计数据
            
        返回:
            历史经验提示词上下文
        """
        # 获取成功和失败模式
        success_patterns = self.get_most_common_patterns(pattern_type="success", limit=3)
        failure_patterns = self.get_most_common_patterns(pattern_type="failure", limit=3)
        
        # 构建上下文
        context = f"## 历史交易经验总结 ({self.symbol})\n\n"
        
        # 添加整体统计
        if stats:
            context += "### 交易统计\n"
            context += f"- 总交易次数: {stats['total_trades']}\n"
            context += f"- 胜率: {stats['win_rate']:.2%}\n"
            context += f"- 盈亏比: {stats['profit_factor']:.2f}\n"
        
        # 添加成功模式
        if success_patterns:
            context += "\n### 成功模式\n"
            for i, pattern in enumerate(success_patterns, 1):
                context += f"{i}. **{pattern['pattern_type']}**: {pattern['value']}\n"
                context += f"   - 发生次数: {pattern['occurrences']}\n"
                context += f"   - 平均盈亏: ${pattern['avg_pnl']:.2f}\n"
        
        # 添加失败模式
        if failure_patterns:
            context += "\n### 失败模式 (应避免)\n"
            for i, pattern in enumerate(failure_patterns, 1):
                context += f"{i}. **{pattern['pattern_type']}**: {pattern['value']}\n"
                context += f"   - 发生次数: {pattern['occurrences']}\n"
                context += f"   - 平均亏损: ${pattern['avg_pnl']:.2f}\n"
        
        # 添加特定交易类型的建议
        if trade_type == "option":
            context += "\n### 期权交易经验\n"
            context += "- 考虑IV因素: 高IV环境下卖出期权可能更有优势\n"
            context += "- 留意到期时间: 接近到期日的期权时间衰减加速\n"
            context += "- 留意突发事件: 盈利交易可能被突发消息逆转\n"
        
        return context

# 辅助函数
def calculate_trade_correlations(trades: List[Dict]) -> Dict:
    """
    计算交易特征之间的相关性
    
    参数:
        trades: 交易记录列表
        
    返回:
        特征相关性字典
    """
    if not trades:
        return {}
    
    # 创建DataFrame
    df = pd.DataFrame(trades)
    
    # 提取数值特征
    numeric_cols = []
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_cols.append(col)
    
    # 计算相关性
    if len(numeric_cols) > 1:
        corr_matrix = df[numeric_cols].corr()
        
        # 转换为字典格式
        correlations = {}
        for i, col1 in enumerate(numeric_cols):
            for col2 in numeric_cols[i+1:]:
                corr_value = corr_matrix.loc[col1, col2]
                if not pd.isna(corr_value):
                    correlations[f"{col1}_vs_{col2}"] = corr_value
        
        return correlations
    
    return {} 