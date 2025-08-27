"""
AI图表报告生成器
生成交易策略绩效的可视化图表，并支持发送到Telegram
"""

import os
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from typing import Optional, Dict, List, Any, Union, Tuple
import json
import telegram
from telegram import Bot

logger = logging.getLogger(__name__)

class AIChartReporter:
    """AI图表报告生成器"""
    
    def __init__(self, telegram_token: Optional[str] = None, telegram_chat_id: Optional[str] = None):
        """
        初始化图表报告生成器
        
        Args:
            telegram_token: Telegram Bot Token，如果不提供则从环境变量读取
            telegram_chat_id: Telegram Chat ID，如果不提供则从环境变量读取
        """
        self.telegram_token = telegram_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = telegram_chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        
        if not self.telegram_token:
            logger.warning("未设置TELEGRAM_BOT_TOKEN环境变量，Telegram推送功能将被禁用")
        
        if not self.telegram_chat_id:
            logger.warning("未设置TELEGRAM_CHAT_ID环境变量，Telegram推送功能将被禁用")
        
        # 创建图表临时目录
        self.charts_dir = Path("temp_charts")
        self.charts_dir.mkdir(exist_ok=True)
        
        # 设置默认样式
        self._set_matplotlib_style()
    
    def _set_matplotlib_style(self):
        """设置Matplotlib图表样式"""
        plt.style.use('dark_background')
        sns.set_style("darkgrid")
        
        # 自定义样式设定
        plt.rcParams['figure.figsize'] = (10, 6)
        plt.rcParams['axes.titlesize'] = 16
        plt.rcParams['axes.labelsize'] = 12
        plt.rcParams['xtick.labelsize'] = 10
        plt.rcParams['ytick.labelsize'] = 10
        plt.rcParams['legend.fontsize'] = 10
        plt.rcParams['axes.grid'] = True
        plt.rcParams['grid.alpha'] = 0.3
    
    def _get_chart_path(self, chart_type: str) -> str:
        """生成图表文件路径"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return str(self.charts_dir / f"{chart_type}_{timestamp}.png")
    
    def generate_pnl_chart(self, 
                         pnl_data: Union[pd.Series, List[float], Dict[str, float]], 
                         title: str = "交易盈亏走势") -> Dict[str, Any]:
        """
        生成盈亏曲线图
        
        Args:
            pnl_data: 盈亏数据，可以是Series、List或者带时间戳的Dict
            title: 图表标题
            
        Returns:
            包含图表路径和状态的字典
        """
        try:
            # 将不同格式的输入转换为pandas Series
            if isinstance(pnl_data, list):
                pnl_series = pd.Series(pnl_data)
            elif isinstance(pnl_data, dict):
                pnl_series = pd.Series(pnl_data)
            else:
                pnl_series = pnl_data
            
            # 计算累积盈亏
            if not pnl_series.empty:
                cum_pnl = pnl_series.cumsum()
            else:
                return {"success": False, "error": "盈亏数据为空"}
            
            # 创建图表
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # 绘制累积盈亏曲线
            ax.plot(cum_pnl.index, cum_pnl.values, 
                   linewidth=2, 
                   marker='o', 
                   markersize=4, 
                   label="累计盈亏")
            
            # 添加零线
            ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
            
            # 标记正负区域
            ax.fill_between(cum_pnl.index, cum_pnl.values, 0,
                          where=(cum_pnl.values > 0),
                          color='green', alpha=0.3)
            ax.fill_between(cum_pnl.index, cum_pnl.values, 0,
                          where=(cum_pnl.values < 0),
                          color='red', alpha=0.3)
            
            # 标记最大回撤区域
            def calculate_drawdown(equity_curve):
                """计算回撤序列"""
                running_max = np.maximum.accumulate(equity_curve)
                drawdown = (equity_curve - running_max) / running_max
                return drawdown
            
            drawdown = calculate_drawdown(cum_pnl.values)
            max_dd_idx = np.argmin(drawdown)
            if max_dd_idx > 0:
                high_idx = np.argmax(cum_pnl.values[:max_dd_idx+1])
                ax.plot([cum_pnl.index[high_idx], cum_pnl.index[max_dd_idx]],
                       [cum_pnl.values[high_idx], cum_pnl.values[max_dd_idx]],
                       'r--', linewidth=1.5, alpha=0.7)
                ax.fill_between([cum_pnl.index[high_idx], cum_pnl.index[max_dd_idx]],
                              [cum_pnl.values[high_idx], cum_pnl.values[high_idx]],
                              [cum_pnl.values[high_idx], cum_pnl.values[max_dd_idx]],
                              color='red', alpha=0.2, label='最大回撤')
            
            # 设置图表样式
            ax.set_title(title, fontweight='bold')
            ax.set_xlabel('时间/交易次数')
            ax.set_ylabel('累计盈亏 ($)')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # 显示关键统计信息
            total_pnl = cum_pnl.iloc[-1] if len(cum_pnl) > 0 else 0
            max_drawdown = abs(np.min(drawdown)) * 100 if len(drawdown) > 0 else 0
            win_rate = np.sum(pnl_series > 0) / len(pnl_series) * 100 if len(pnl_series) > 0 else 0
            
            stats_text = (
                f"总盈亏: ${total_pnl:.2f}\n"
                f"最大回撤: {max_drawdown:.2f}%\n"
                f"胜率: {win_rate:.1f}%"
            )
            
            # 添加统计信息文本框
            ax.text(0.02, 0.05, stats_text, transform=ax.transAxes,
                  bbox=dict(facecolor='black', alpha=0.7, boxstyle='round,pad=0.5'))
            
            # 调整布局
            plt.tight_layout()
            
            # 保存图表
            chart_path = self._get_chart_path('pnl_chart')
            plt.savefig(chart_path, dpi=100, bbox_inches='tight')
            plt.close()
            
            return {
                "success": True,
                "chart_path": chart_path,
                "stats": {
                    "total_pnl": float(total_pnl),
                    "max_drawdown": float(max_drawdown),
                    "win_rate": float(win_rate)
                }
            }
        except Exception as e:
            logger.error(f"生成盈亏图表时出错: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def generate_strategy_distribution_chart(self, 
                                          strategy_results: Dict[str, float],
                                          title: str = "策略盈亏分布") -> Dict[str, Any]:
        """
        生成策略盈亏分布饼图
        
        Args:
            strategy_results: 策略名称到盈亏金额的映射字典
            title: 图表标题
            
        Returns:
            包含图表路径和状态的字典
        """
        try:
            # 分离正负盈亏
            positive_results = {k: v for k, v in strategy_results.items() if v > 0}
            negative_results = {k: v for k, v in strategy_results.items() if v < 0}
            
            # 如果没有数据，返回错误
            if not strategy_results:
                return {"success": False, "error": "策略结果数据为空"}
            
            # 创建图表（2个子图：饼图和条形图）
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))
            
            # 饼图 - 按盈亏比例分布
            abs_values = {k: abs(v) for k, v in strategy_results.items()}
            labels = list(abs_values.keys())
            sizes = list(abs_values.values())
            # 确保所有盈亏的总和为100%
            total = sum(sizes)
            if total == 0:
                sizes = [1] * len(sizes)  # 避免除以零
                
            # 计算每个策略占总盈亏的百分比
            percentages = [s/sum(sizes)*100 for s in sizes]
            
            # 计算高亮突出显示 (将最大的策略突出)
            explode = [0.1 if s == max(sizes) else 0.0 for s in sizes]
            
            # 为正负盈亏设置不同颜色
            colors = []
            for k in labels:
                if k in positive_results:
                    colors.append('green')
                else:
                    colors.append('red')
            
            # 绘制饼图
            wedges, texts, autotexts = ax1.pie(
                sizes, 
                explode=explode,
                labels=None,  # 不在饼图上直接显示标签
                autopct='%1.1f%%',
                startangle=90,
                colors=colors,
                wedgeprops={'linewidth': 1, 'edgecolor': 'white'}
            )
            
            # 设置饼图属性
            for i, autotext in enumerate(autotexts):
                autotext.set_color('white')
                autotext.set_fontsize(9)
            
            # 添加图例
            labels_with_values = [f"{l} (${strategy_results[l]:.0f})" for l in labels]
            ax1.legend(wedges, labels_with_values, 
                     title="策略贡献",
                     loc="center left",
                     bbox_to_anchor=(0.9, 0, 0.5, 1))
            
            ax1.set_title("策略盈亏占比", fontweight='bold')
            
            # 绘制条形图 - 各策略具体盈亏金额
            strategies = list(strategy_results.keys())
            values = list(strategy_results.values())
            
            # 按盈亏金额排序
            sorted_indices = sorted(range(len(values)), key=lambda i: values[i])
            strategies = [strategies[i] for i in sorted_indices]
            values = [values[i] for i in sorted_indices]
            
            bars = ax2.barh(strategies, values)
            
            # 为正负值设置不同颜色
            for i, v in enumerate(values):
                if v >= 0:
                    bars[i].set_color('green')
                else:
                    bars[i].set_color('red')
            
            # 添加数值标签
            for i, v in enumerate(values):
                ax2.text(v + (5 if v >= 0 else -5), 
                       i, 
                       f"${v:.0f}", 
                       va='center',
                       ha='left' if v >= 0 else 'right',
                       fontweight='bold',
                       color='white')
            
            # 设置条形图属性
            ax2.set_title("策略具体盈亏", fontweight='bold')
            ax2.set_xlabel('盈亏金额 ($)')
            ax2.axvline(x=0, color='gray', linestyle='--', alpha=0.7)
            ax2.grid(True, alpha=0.3)
            
            # 总盈亏统计
            total_pnl = sum(strategy_results.values())
            total_pos = sum(v for v in strategy_results.values() if v > 0)
            total_neg = sum(v for v in strategy_results.values() if v < 0)
            
            stats_text = (
                f"总盈亏: ${total_pnl:.0f}\n"
                f"盈利策略: ${total_pos:.0f}\n"
                f"亏损策略: ${total_neg:.0f}"
            )
            
            # 在条形图上添加统计信息
            ax2.text(0.02, 0.02, stats_text, transform=ax2.transAxes,
                   bbox=dict(facecolor='black', alpha=0.7, boxstyle='round,pad=0.5'))
            
            # 设置整体标题
            plt.suptitle(title, fontsize=16, fontweight='bold')
            
            # 调整布局
            plt.tight_layout()
            fig.subplots_adjust(top=0.9)
            
            # 保存图表
            chart_path = self._get_chart_path('strategy_distribution')
            plt.savefig(chart_path, dpi=100, bbox_inches='tight')
            plt.close()
            
            return {
                "success": True,
                "chart_path": chart_path,
                "stats": {
                    "total_pnl": float(total_pnl),
                    "total_positive": float(total_pos),
                    "total_negative": float(total_neg),
                    "best_strategy": max(strategy_results.items(), key=lambda x: x[1])[0],
                    "worst_strategy": min(strategy_results.items(), key=lambda x: x[1])[0]
                }
            }
        except Exception as e:
            logger.error(f"生成策略分布图表时出错: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def generate_performance_metrics_chart(self,
                                        metrics: Dict[str, float],
                                        comparison_metrics: Optional[Dict[str, float]] = None,
                                        title: str = "策略绩效指标") -> Dict[str, Any]:
        """
        生成绩效指标雷达图
        
        Args:
            metrics: 绩效指标字典，如 {'Sharpe': 1.2, 'Sortino': 1.5, ...}
            comparison_metrics: 可选的对比指标，如基准指标
            title: 图表标题
            
        Returns:
            包含图表路径和状态的字典
        """
        try:
            if not metrics:
                return {"success": False, "error": "绩效指标数据为空"}
            
            # 准备雷达图数据
            categories = list(metrics.keys())
            values = list(metrics.values())
            
            # 标准化值到0-1范围便于雷达图显示
            max_values = [max(1.0, abs(v)) for v in values]  # 避免除以零
            norm_values = [v / max_v for v, max_v in zip(values, max_values)]
            
            # 计算角度
            N = len(categories)
            angles = [n / float(N) * 2 * np.pi for n in range(N)]
            angles += angles[:1]  # 闭合雷达图
            
            # 标准化值添加闭合点
            norm_values += norm_values[:1]
            
            # 比较数据（如果提供）
            if comparison_metrics:
                comp_values = [comparison_metrics.get(cat, 0) for cat in categories]
                comp_norm_values = [cv / max_v for cv, max_v in zip(comp_values, max_values)]
                comp_norm_values += comp_norm_values[:1]  # 闭合
            
            # 创建图表
            fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
            
            # 绘制背景网格
            ax.fill(angles, [1]*len(angles), color='gray', alpha=0.1)
            
            # 绘制主要数据
            ax.plot(angles, norm_values, 'o-', linewidth=2, color='green', label='当前策略')
            ax.fill(angles, norm_values, color='green', alpha=0.25)
            
            # 绘制比较数据（如果有）
            if comparison_metrics:
                ax.plot(angles, comp_norm_values, 'o-', linewidth=2, color='blue', label='基准')
                ax.fill(angles, comp_norm_values, color='blue', alpha=0.1)
            
            # 设置雷达图属性
            ax.set_thetagrids(np.degrees(angles[:-1]), categories)
            ax.set_ylim(0, 1)
            ax.set_yticks([])  # 移除径向刻度
            ax.grid(True, alpha=0.3)
            
            # 添加具体数值标签
            for i, (angle, category, value) in enumerate(zip(angles[:-1], categories, values)):
                ha = 'left' if 0 <= angle < np.pi else 'right'
                ax.text(angle, 1.1, f"{category}: {value:.2f}", 
                      size=9, 
                      ha=ha,
                      va='center',
                      bbox=dict(facecolor='black', alpha=0.7, boxstyle='round,pad=0.2'))
            
            # 添加标题和图例
            ax.set_title(title, size=15, pad=20, fontweight='bold')
            if comparison_metrics:
                ax.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
            
            # 保存图表
            chart_path = self._get_chart_path('performance_metrics')
            plt.savefig(chart_path, dpi=100, bbox_inches='tight')
            plt.close()
            
            return {
                "success": True,
                "chart_path": chart_path,
                "metrics": metrics
            }
        except Exception as e:
            logger.error(f"生成绩效指标图表时出错: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_chart_to_telegram(self, chart_path: str, caption: Optional[str] = None) -> bool:
        """
        发送图表到Telegram
        
        Args:
            chart_path: 图表文件路径
            caption: 可选的图表说明
            
        Returns:
            是否发送成功
        """
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("未设置Telegram配置，图表发送失败")
            return False
        
        try:
            bot = Bot(token=self.telegram_token)
            with open(chart_path, 'rb') as chart_file:
                if caption:
                    bot.send_photo(
                        chat_id=self.telegram_chat_id, 
                        photo=chart_file, 
                        caption=caption
                    )
                else:
                    bot.send_photo(
                        chat_id=self.telegram_chat_id, 
                        photo=chart_file
                    )
            
            logger.info(f"成功发送图表到Telegram: {chart_path}")
            return True
        except Exception as e:
            logger.error(f"发送图表到Telegram时出错: {str(e)}")
            return False
    
    def generate_and_send_pnl_chart(self, 
                                  pnl_data: Union[pd.Series, List[float], Dict[str, float]], 
                                  title: str = "交易盈亏走势",
                                  caption: Optional[str] = None) -> Dict[str, Any]:
        """
        生成并发送盈亏曲线图到Telegram
        
        Args:
            pnl_data: 盈亏数据
            title: 图表标题
            caption: Telegram消息说明
            
        Returns:
            操作结果字典
        """
        # 生成图表
        result = self.generate_pnl_chart(pnl_data, title)
        
        if not result["success"]:
            return result
        
        # 如果未提供caption，则自动生成一个
        if not caption:
            stats = result["stats"]
            caption = (
                f"📊 *{title}*\n\n"
                f"总盈亏: ${stats['total_pnl']:.2f}\n"
                f"最大回撤: {stats['max_drawdown']:.2f}%\n"
                f"胜率: {stats['win_rate']:.1f}%"
            )
        
        # 发送到Telegram
        sent = self.send_chart_to_telegram(result["chart_path"], caption)
        
        # 更新结果
        result["telegram_sent"] = sent
        
        # 清理临时文件
        try:
            if os.path.exists(result["chart_path"]):
                os.unlink(result["chart_path"])
        except OSError:
            pass
        
        return result
    
    def generate_and_send_strategy_chart(self, 
                                      strategy_results: Dict[str, float],
                                      title: str = "策略盈亏分布",
                                      caption: Optional[str] = None) -> Dict[str, Any]:
        """
        生成并发送策略分布图到Telegram
        
        Args:
            strategy_results: 策略盈亏字典
            title: 图表标题
            caption: Telegram消息说明
            
        Returns:
            操作结果字典
        """
        # 生成图表
        result = self.generate_strategy_distribution_chart(strategy_results, title)
        
        if not result["success"]:
            return result
        
        # 如果未提供caption，则自动生成一个
        if not caption:
            stats = result["stats"]
            caption = (
                f"📊 *{title}*\n\n"
                f"总盈亏: ${stats['total_pnl']:.2f}\n"
                f"最佳策略: {stats['best_strategy']}\n"
                f"表现欠佳: {stats['worst_strategy']}"
            )
        
        # 发送到Telegram
        sent = self.send_chart_to_telegram(result["chart_path"], caption)
        
        # 更新结果
        result["telegram_sent"] = sent
        
        # 清理临时文件
        try:
            if os.path.exists(result["chart_path"]):
                os.unlink(result["chart_path"])
        except OSError:
            pass
        
        return result

# 单例模式，方便直接导入使用
chart_reporter = AIChartReporter()

# 测试代码
if __name__ == "__main__":
    # 测试PnL图表
    sample_pnl = pd.Series([100, -50, 200, 150, -120, 300, 250, -80, 100, 200])
    
    pnl_result = chart_reporter.generate_and_send_pnl_chart(
        sample_pnl,
        title="今日交易盈亏曲线",
        caption="📈 今日交易业绩图表"
    )
    
    print(f"PnL图表发送结果: {'成功' if pnl_result.get('telegram_sent', False) else '失败'}")
    
    # 测试策略分布图
    strategy_results = {
        "Mean Reversion": 340.0,
        "Gamma Scalping": 520.0,
        "Breakout V2": -120.0,
        "RSI Strategy": 250.0,
        "Options Flow": -80.0
    }
    
    strategy_result = chart_reporter.generate_and_send_strategy_chart(
        strategy_results,
        title="今日策略绩效分布",
        caption="📊 策略盈亏分析"
    )
    
    print(f"策略图表发送结果: {'成功' if strategy_result.get('telegram_sent', False) else '失败'}") 