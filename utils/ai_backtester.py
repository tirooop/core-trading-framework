#!/usr/bin/env python3
"""
AI Backtester

This module provides functionality to backtest AI-generated trading signals and strategies.
It calculates hit rates, profit distributions, and other performance metrics to help
evaluate and improve AI trading strategies.
"""

import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional, Union

# Add project root to path if needed
from utils.ai_knowledge_base import AIKnowledgeBase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AIBacktester")

class AIBacktester:
    """
    AI策略回测器
    用于评估AI策略的命中率、收益分布和性能指标
    """
    
    def __init__(self, knowledge_base_dir="data/knowledge_base"):
        """
        初始化AI回测器
        
        Args:
            knowledge_base_dir: 知识库数据目录
        """
        self.knowledge_base = AIKnowledgeBase(data_dir=knowledge_base_dir)
        self.results_dir = Path("data/backtest_results")
        self.results_dir.mkdir(exist_ok=True, parents=True)
        
    def review(self, symbol=None, days=30, min_confidence=0.5) -> Dict[str, Any]:
        """
        回测AI策略并计算命中率、收益分布等指标
        
        Args:
            symbol: 特定股票代码，如果为None则回测所有股票
            days: 回测天数
            min_confidence: 最低置信度过滤
            
        Returns:
            包含回测结果的字典
        """
        # 获取所有信号
        signals = self.knowledge_base.query_signals(symbol=symbol)
        
        # 按时间过滤最近N天的信号
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_signals = [
            signal for signal in signals 
            if datetime.fromisoformat(signal.get('timestamp', '2000-01-01T00:00:00')).replace(tzinfo=None) > cutoff_date
            and float(signal.get('confidence', 0)) >= min_confidence
        ]
        
        if not recent_signals:
            logger.warning(f"没有找到符合条件的信号进行回测 (symbol={symbol}, days={days})")
            return {
                "status": "warning",
                "message": "没有足够的数据进行回测",
                "hit_rate": 0,
                "signals_count": 0
            }
        
        # 计算命中率
        hit_count = sum(1 for signal in recent_signals if signal.get('hit', False))
        hit_rate = hit_count / len(recent_signals) if recent_signals else 0
        
        # 按置信度分组分析
        confidence_bins = {
            'low': [0.5, 0.7],
            'medium': [0.7, 0.85],
            'high': [0.85, 1.0]
        }
        
        confidence_performance = {}
        for level, (lower, upper) in confidence_bins.items():
            level_signals = [
                signal for signal in recent_signals
                if lower <= float(signal.get('confidence', 0)) < upper
            ]
            
            level_hit_count = sum(1 for signal in level_signals if signal.get('hit', False))
            level_hit_rate = level_hit_count / len(level_signals) if level_signals else 0
            
            confidence_performance[level] = {
                'count': len(level_signals),
                'hit_rate': level_hit_rate,
                'avg_profit': self._calculate_avg_profit(level_signals)
            }
        
        # 按动作分组分析 (Call/Put/Hold)
        action_performance = {}
        for action in ['Call', 'Put', 'Hold']:
            action_signals = [
                signal for signal in recent_signals
                if signal.get('action') == action
            ]
            
            action_hit_count = sum(1 for signal in action_signals if signal.get('hit', False))
            action_hit_rate = action_hit_count / len(action_signals) if action_signals else 0
            
            action_performance[action] = {
                'count': len(action_signals),
                'hit_rate': action_hit_rate,
                'avg_profit': self._calculate_avg_profit(action_signals)
            }
            
        # 按股票代码分组
        symbol_performance = {}
        if not symbol:  # 只有在回测所有股票时才分析
            symbols = set(signal.get('symbol') for signal in recent_signals)
            for sym in symbols:
                sym_signals = [
                    signal for signal in recent_signals
                    if signal.get('symbol') == sym
                ]
                
                sym_hit_count = sum(1 for signal in sym_signals if signal.get('hit', False))
                sym_hit_rate = sym_hit_count / len(sym_signals) if sym_signals else 0
                
                symbol_performance[sym] = {
                    'count': len(sym_signals),
                    'hit_rate': sym_hit_rate,
                    'avg_profit': self._calculate_avg_profit(sym_signals)
                }
        
        # 生成回测报告
        report = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "signals_count": len(recent_signals),
            "hit_count": hit_count,
            "hit_rate": hit_rate,
            "avg_profit": self._calculate_avg_profit(recent_signals),
            "confidence_performance": confidence_performance,
            "action_performance": action_performance,
            "symbol_performance": symbol_performance,
            "period_days": days
        }
        
        # 保存回测结果
        self._save_report(report, symbol)
        
        return report
    
    def _calculate_avg_profit(self, signals):
        """计算平均收益率"""
        profits = [float(signal.get('profit_pct', 0)) for signal in signals if 'profit_pct' in signal]
        return sum(profits) / len(profits) if profits else 0
    
    def _save_report(self, report, symbol=None):
        """保存回测报告"""
        filename = f"backtest_{symbol or 'all'}_{datetime.now().strftime('%Y%m%d')}.json"
        with open(self.results_dir / filename, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"回测报告已保存: {filename}")
    
    def generate_performance_chart(self, report=None, symbol=None, days=30):
        """生成性能图表"""
        if report is None:
            report = self.review(symbol=symbol, days=days)
        
        # 创建图表
        fig = go.Figure()
        
        # 添加整体命中率
        fig.add_trace(go.Indicator(
            mode = "gauge+number",
            value = report['hit_rate'] * 100,
            title = {'text': f"AI命中率 ({report['signals_count']}信号)"},
            domain = {'x': [0, 1], 'y': [0, 0.3]},
            gauge = {
                'axis': {'range': [0, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 70], 'color': "cyan"},
                    {'range': [70, 85], 'color': "royalblue"},
                    {'range': [85, 100], 'color': "darkblue"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 70
                }
            }
        ))
        
        # 按置信度分组的性能
        confidence_levels = list(report['confidence_performance'].keys())
        hit_rates = [report['confidence_performance'][level]['hit_rate'] * 100 for level in confidence_levels]
        counts = [report['confidence_performance'][level]['count'] for level in confidence_levels]
        
        # 添加置信度柱状图
        fig.add_trace(go.Bar(
            x=confidence_levels,
            y=hit_rates,
            text=[f"{rate:.1f}% ({cnt})" for rate, cnt in zip(hit_rates, counts)],
            textposition='auto',
            name='按置信度命中率',
            marker_color='royalblue'
        ))
        
        # 设置布局
        fig.update_layout(
            title=f"AI策略回测分析 - {'所有标的' if symbol is None else symbol} ({days}天)",
            yaxis=dict(title='命中率 (%)'),
            barmode='group',
            height=600
        )
        
        return fig
    
    def get_symbol_performance(self, days=30, min_signals=5):
        """获取每个标的的性能数据"""
        report = self.review(days=days)
        symbol_perf = report['symbol_performance']
        
        # 过滤掉信号数量少于阈值的标的
        filtered_perf = {
            sym: data for sym, data in symbol_perf.items()
            if data['count'] >= min_signals
        }
        
        if not filtered_perf:
            return None
            
        # 按命中率排序
        sorted_perf = sorted(
            filtered_perf.items(),
            key=lambda x: x[1]['hit_rate'],
            reverse=True
        )
        
        return sorted_perf
    
    def export_to_csv(self, symbol=None, days=30):
        """导出回测结果到CSV"""
        signals = self.knowledge_base.query_signals(symbol=symbol)
        
        # 按时间过滤最近N天的信号
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_signals = [
            signal for signal in signals 
            if datetime.fromisoformat(signal.get('timestamp', '2000-01-01T00:00:00')).replace(tzinfo=None) > cutoff_date
        ]
        
        if not recent_signals:
            logger.warning(f"没有找到符合条件的信号导出 (symbol={symbol}, days={days})")
            return None
        
        # 转换为DataFrame
        df = pd.DataFrame(recent_signals)
        
        # 导出到CSV
        filename = f"ai_signals_{symbol or 'all'}_{datetime.now().strftime('%Y%m%d')}.csv"
        export_path = self.results_dir / filename
        df.to_csv(export_path, index=False)
        logger.info(f"信号数据已导出: {export_path}")
        
        return export_path


if __name__ == "__main__":
    # 简单测试
    backtester = AIBacktester()
    report = backtester.review(days=30)
    print(f"整体命中率: {report['hit_rate']*100:.2f}%")
    print(f"信号数量: {report['signals_count']}") 