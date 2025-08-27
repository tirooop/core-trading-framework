"""
交易记忆库可视化模块 - 交易历史可视化工具
AI量化系统6.0 - 交易记忆与自学习闭环的可视化组件
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import logging
from typing import Dict, List, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("trade_memory_visualization")

class TradeVisualizer:
    """交易可视化器 - 生成交易历史的可视化图表"""
    
    def __init__(self, memory_dir: str, symbol: str):
        """
        初始化交易可视化器
        
        参数:
            memory_dir: 记忆库存储目录
            symbol: 交易标的代码
        """
        self.memory_dir = memory_dir
        self.symbol = symbol
        self.viz_dir = os.path.join(memory_dir, "visualizations")
        
        # 确保可视化目录存在
        os.makedirs(self.viz_dir, exist_ok=True)
    
    def visualize_trades(self, 
                        trades: List[Dict],
                        start_date: Optional[str] = None, 
                        end_date: Optional[str] = None,
                        save_path: Optional[str] = None) -> str:
        """
        可视化交易历史
        
        参数:
            trades: 交易记录列表
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            save_path: 保存路径，默认为记忆库可视化目录
            
        返回:
            保存的图表路径
        """
        if not trades:
            logger.warning("没有交易数据可供可视化")
            return ""
        
        # 创建图表
        plt.figure(figsize=(12, 10))
        
        # 创建4个子图
        fig, axs = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. 资金曲线图
        trades_df = pd.DataFrame(trades)
        if 'entry_time' in trades_df.columns:
            trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
            trades_df = trades_df.sort_values('entry_time')
            
            # 计算累计盈亏
            trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
            
            axs[0, 0].plot(trades_df['entry_time'], trades_df['cumulative_pnl'], 'b-')
            axs[0, 0].set_title('Cumulative P&L')
            axs[0, 0].set_xlabel('Date')
            axs[0, 0].set_ylabel('P&L ($)')
            axs[0, 0].grid(True)
            
            # 添加零线
            axs[0, 0].axhline(y=0, color='r', linestyle='-', alpha=0.3)
        
        # 2. 盈亏分布图
        sns.histplot(trades_df['pnl'], kde=True, ax=axs[0, 1])
        axs[0, 1].set_title('P&L Distribution')
        axs[0, 1].set_xlabel('P&L ($)')
        axs[0, 1].set_ylabel('Frequency')
        axs[0, 1].axvline(x=0, color='r', linestyle='-', alpha=0.3)
        
        # 3. 胜率按因素分类
        if 'market_condition' in trades_df.columns:
            # 计算每种市场条件的胜率
            win_rates = []
            conditions = []
            
            for condition in trades_df['market_condition'].unique():
                condition_trades = trades_df[trades_df['market_condition'] == condition]
                win_rate = (condition_trades['pnl'] > 0).mean()
                count = len(condition_trades)
                
                # 只显示有足够样本的条件
                if count >= 3:
                    win_rates.append(win_rate)
                    conditions.append(f"{condition} (n={count})")
            
            # 绘制胜率条形图
            if conditions:
                axs[1, 0].bar(conditions, win_rates)
                axs[1, 0].set_title('Win Rate by Market Condition')
                axs[1, 0].set_ylabel('Win Rate')
                axs[1, 0].set_ylim(0, 1)
                plt.setp(axs[1, 0].get_xticklabels(), rotation=45, ha='right')
        
        # 4. 平均盈亏按方向分类
        if 'direction' in trades_df.columns:
            direction_pnl = trades_df.groupby('direction')['pnl'].agg(['mean', 'count'])
            
            directions = [f"{d} (n={c})" for d, c in zip(direction_pnl.index, direction_pnl['count'])]
            means = direction_pnl['mean']
            
            axs[1, 1].bar(directions, means)
            axs[1, 1].set_title('Average P&L by Direction')
            axs[1, 1].set_ylabel('Average P&L ($)')
            
            # 添加零线
            axs[1, 1].axhline(y=0, color='r', linestyle='-', alpha=0.3)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存图表
        if not save_path:
            date_range = ""
            if start_date:
                date_range += f"_{start_date}"
            if end_date:
                date_range += f"_to_{end_date}"
                
            save_path = os.path.join(self.viz_dir, 
                               f"{self.symbol}_trades{date_range}.png")
        
        plt.savefig(save_path)
        plt.close()
        
        logger.info(f"已保存交易可视化图表: {save_path}")
        return save_path
    
    def plot_trade_analysis(self, 
                           trades: List[Dict],
                           plot_type: str = "monthly",
                           save_path: Optional[str] = None) -> str:
        """
        绘制交易分析图表
        
        参数:
            trades: 交易记录列表
            plot_type: 图表类型 ("monthly", "weekly", "daily", "by_factor")
            save_path: 保存路径
            
        返回:
            保存的图表路径
        """
        if not trades:
            logger.warning("没有交易数据可供分析")
            return ""
        
        # 创建DataFrame
        trades_df = pd.DataFrame(trades)
        if 'entry_time' not in trades_df.columns:
            logger.warning("交易数据缺少entry_time字段")
            return ""
            
        trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
        
        # 根据图表类型进行不同的处理
        if plot_type == "monthly":
            # 按月份统计
            trades_df['month'] = trades_df['entry_time'].dt.to_period('M')
            monthly_stats = trades_df.groupby('month').agg({
                'pnl': ['sum', 'mean', 'count'],
                'trade_id': 'count'
            })
            
            # 调整列名
            monthly_stats.columns = ['total_pnl', 'avg_pnl', 'pnl_count', 'trade_count']
            
            # 计算胜率
            monthly_stats['win_rate'] = trades_df.groupby('month').apply(
                lambda x: (x['pnl'] > 0).mean()
            )
            
            # 绘图
            fig, ax1 = plt.subplots(figsize=(12, 6))
            
            # 绘制总盈亏柱状图
            monthly_stats['total_pnl'].plot(kind='bar', ax=ax1, color='b', alpha=0.6)
            ax1.set_ylabel('Total P&L ($)')
            ax1.set_title('Monthly Trading Performance')
            
            # 添加胜率折线图
            ax2 = ax1.twinx()
            monthly_stats['win_rate'].plot(kind='line', ax=ax2, color='r', marker='o')
            ax2.set_ylabel('Win Rate')
            ax2.set_ylim(0, 1)
            
            # 调整布局
            plt.xticks(rotation=45)
            plt.tight_layout()
            
        elif plot_type == "by_factor":
            # 按因素分析
            fig, axs = plt.subplots(2, 2, figsize=(15, 12))
            
            # 1. 市场条件分析
            if 'market_condition' in trades_df.columns:
                market_pnl = trades_df.groupby('market_condition')['pnl'].agg(['mean', 'count'])
                market_pnl = market_pnl.sort_values('mean', ascending=False)
                
                # 只显示样本数>=3的条件
                market_pnl = market_pnl[market_pnl['count'] >= 3]
                
                if not market_pnl.empty:
                    # 创建条形图
                    market_pnl['mean'].plot(kind='bar', ax=axs[0, 0], 
                                           yerr=trades_df.groupby('market_condition')['pnl'].std())
                    axs[0, 0].set_title('Average P&L by Market Condition')
                    axs[0, 0].set_ylabel('Avg P&L ($)')
                    
                    # 添加样本数量标签
                    for i, v in enumerate(market_pnl['mean']):
                        axs[0, 0].text(i, v, f"n={market_pnl['count'].iloc[i]}", 
                                      ha='center', va='bottom' if v > 0 else 'top')
            
            # 2. AI置信度分析
            if 'ai_confidence' in trades_df.columns:
                # 将置信度分成5个区间
                trades_df['confidence_bin'] = pd.cut(trades_df['ai_confidence'], 
                                                   bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
                                                   labels=['0-0.2', '0.2-0.4', '0.4-0.6', '0.6-0.8', '0.8-1.0'])
                
                confidence_stats = trades_df.groupby('confidence_bin').agg({
                    'pnl': ['mean', 'count'],
                    'trade_id': 'count'
                })
                
                # 绘制散点图
                if not confidence_stats.empty:
                    axs[0, 1].scatter(trades_df['ai_confidence'], trades_df['pnl'])
                    axs[0, 1].set_title('P&L vs AI Confidence')
                    axs[0, 1].set_xlabel('AI Confidence')
                    axs[0, 1].set_ylabel('P&L ($)')
                    axs[0, 1].grid(True)
                    
                    # 添加拟合线
                    from scipy import stats
                    slope, intercept, r_value, p_value, std_err = stats.linregress(
                        trades_df['ai_confidence'], trades_df['pnl']
                    )
                    x = np.array([min(trades_df['ai_confidence']), max(trades_df['ai_confidence'])])
                    y = slope * x + intercept
                    axs[0, 1].plot(x, y, 'r-', 
                                  label=f'R²={r_value**2:.2f}, p={p_value:.3f}')
                    axs[0, 1].legend()
            
            # 3. 时间分析
            trades_df['hour'] = trades_df['entry_time'].dt.hour
            hour_stats = trades_df.groupby('hour')['pnl'].mean()
            
            axs[1, 0].bar(hour_stats.index, hour_stats.values)
            axs[1, 0].set_title('Average P&L by Hour of Day')
            axs[1, 0].set_xlabel('Hour')
            axs[1, 0].set_ylabel('Avg P&L ($)')
            axs[1, 0].set_xticks(range(0, 24, 2))
            
            # 4. 交易持续时间分析
            if 'exit_time' in trades_df.columns:
                trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
                trades_df['duration_hours'] = (trades_df['exit_time'] - trades_df['entry_time']).dt.total_seconds() / 3600
                
                # 创建散点图
                sc = axs[1, 1].scatter(trades_df['duration_hours'], trades_df['pnl'],
                                      c=trades_df['pnl'] > 0, cmap='coolwarm', alpha=0.7)
                axs[1, 1].set_title('P&L vs Trade Duration')
                axs[1, 1].set_xlabel('Duration (hours)')
                axs[1, 1].set_ylabel('P&L ($)')
                axs[1, 1].grid(True)
                plt.colorbar(sc, ax=axs[1, 1], label='Win/Loss')
        
        else:
            logger.warning(f"不支持的图表类型: {plot_type}")
            return ""
        
        # 调整布局
        plt.tight_layout()
        
        # 保存图表
        if not save_path:
            save_path = os.path.join(self.viz_dir, 
                               f"{self.symbol}_{plot_type}_analysis.png")
        
        plt.savefig(save_path)
        plt.close()
        
        logger.info(f"已保存交易分析图表: {save_path}")
        return save_path
    
    def create_performance_dashboard(self, 
                                   trades: List[Dict],
                                   save_path: Optional[str] = None) -> str:
        """
        创建性能仪表盘
        
        参数:
            trades: 交易记录列表
            save_path: 保存路径
            
        返回:
            保存的仪表盘路径
        """
        if not trades:
            logger.warning("没有交易数据可供分析")
            return ""
        
        # 创建DataFrame
        trades_df = pd.DataFrame(trades)
        
        # 计算基本统计数据
        total_trades = len(trades_df)
        winning_trades = (trades_df['pnl'] > 0).sum()
        losing_trades = (trades_df['pnl'] < 0).sum()
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_profit = trades_df['pnl'].sum()
        avg_profit = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
        
        # 创建仪表盘
        fig = plt.figure(figsize=(14, 10))
        fig.suptitle(f"{self.symbol} Trading Performance Dashboard", fontsize=16)
        
        # 网格布局
        gs = fig.add_gridspec(3, 3)
        
        # 1. 累计盈亏曲线
        ax1 = fig.add_subplot(gs[0, :])
        if 'entry_time' in trades_df.columns:
            trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
            trades_df = trades_df.sort_values('entry_time')
            trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
            
            ax1.plot(trades_df['entry_time'], trades_df['cumulative_pnl'], 'b-')
            ax1.set_title('Cumulative P&L')
            ax1.set_ylabel('P&L ($)')
            ax1.grid(True)
            ax1.axhline(y=0, color='r', linestyle='-', alpha=0.3)
        
        # 2. 胜率饼图
        ax2 = fig.add_subplot(gs[1, 0])
        ax2.pie([winning_trades, losing_trades], 
               labels=['Wins', 'Losses'], 
               autopct='%1.1f%%',
               colors=['green', 'red'])
        ax2.set_title(f'Win Rate: {win_rate:.1%}')
        
        # 3. 月度绩效热图
        ax3 = fig.add_subplot(gs[1, 1:])
        if 'entry_time' in trades_df.columns:
            # 按月汇总
            trades_df['year'] = trades_df['entry_time'].dt.year
            trades_df['month'] = trades_df['entry_time'].dt.month
            
            monthly_profit = trades_df.pivot_table(
                index='year', 
                columns='month',
                values='pnl',
                aggfunc='sum'
            ).fillna(0)
            
            # 修正月份标签
            month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            monthly_profit.columns = [month_labels[i-1] for i in monthly_profit.columns]
            
            # 绘制热图
            sns.heatmap(monthly_profit, cmap="RdYlGn", center=0, annot=True, fmt=".0f", ax=ax3)
            ax3.set_title('Monthly Performance')
            
        # 4. 关键指标表
        ax4 = fig.add_subplot(gs[2, 0])
        metrics = [
            f"Total Trades: {total_trades}",
            f"Win Rate: {win_rate:.1%}",
            f"Profit Factor: {abs(avg_profit / avg_loss) if avg_loss != 0 else 'N/A'}",
            f"Avg Win: ${avg_profit:.2f}",
            f"Avg Loss: ${avg_loss:.2f}",
            f"Total P&L: ${total_profit:.2f}"
        ]
        
        # 隐藏坐标轴
        ax4.axis('off')
        
        # 添加文本
        y_pos = 0.9
        for metric in metrics:
            ax4.text(0.1, y_pos, metric, fontsize=12)
            y_pos -= 0.15
            
        # 5. 交易方向统计
        ax5 = fig.add_subplot(gs[2, 1])
        if 'direction' in trades_df.columns:
            direction_counts = trades_df['direction'].value_counts()
            ax5.bar(direction_counts.index, direction_counts.values)
            ax5.set_title('Trades by Direction')
            ax5.set_ylabel('Count')
            
            # 添加胜率
            for direction in direction_counts.index:
                direction_df = trades_df[trades_df['direction'] == direction]
                win_rate = (direction_df['pnl'] > 0).mean()
                ax5.text(direction, direction_counts[direction], 
                       f"WR: {win_rate:.1%}", ha='center', va='bottom')
        
        # 6. 盈亏分布
        ax6 = fig.add_subplot(gs[2, 2])
        sns.histplot(trades_df['pnl'], kde=True, ax=ax6)
        ax6.set_title('P&L Distribution')
        ax6.set_xlabel('P&L ($)')
        ax6.axvline(x=0, color='r', linestyle='-', alpha=0.3)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存仪表盘
        if not save_path:
            save_path = os.path.join(self.viz_dir, f"{self.symbol}_dashboard.png")
        
        plt.savefig(save_path)
        plt.close()
        
        logger.info(f"已创建性能仪表盘: {save_path}")
        return save_path 