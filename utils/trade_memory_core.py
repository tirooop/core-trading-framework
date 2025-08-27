"""
交易记忆库核心模块 - 记录、存储和基本分析交易历史
AI量化系统6.0 - 交易记忆与自学习闭环的核心组件
"""
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("trade_memory")

class TradeMemory:
    """
    交易记忆库 - 存储和分析历史交易记录
    支持交易模式识别、交易失败归因、智能优化建议
    """
    
    def __init__(self, memory_dir: str = "data/trade_memory", 
                 symbol: str = "SPY"):
        """
        初始化交易记忆库
        
        参数:
            memory_dir: 记忆库存储目录
            symbol: 交易标的代码
        """
        self.memory_dir = memory_dir
        self.symbol = symbol
        
        # 创建记忆库目录
        self._create_directory_structure()
        
        # 加载现有交易记录
        self.trades = self._load_trades()
        
        # 交易统计数据
        self.stats = {}
        self._update_stats()
        
        logger.info(f"已初始化 {symbol} 交易记忆库，加载 {len(self.trades)} 条交易记录")
    
    def _create_directory_structure(self):
        """创建记忆库目录结构"""
        # 主目录
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # 交易记录子目录
        os.makedirs(os.path.join(self.memory_dir, "trades"), exist_ok=True)
        
        # 分析结果子目录
        os.makedirs(os.path.join(self.memory_dir, "analysis"), exist_ok=True)
        
        # 模式库子目录
        os.makedirs(os.path.join(self.memory_dir, "patterns"), exist_ok=True)
        
        # 可视化子目录
        os.makedirs(os.path.join(self.memory_dir, "visualizations"), exist_ok=True)
    
    def _load_trades(self) -> List[Dict]:
        """加载现有交易记录"""
        trades_file = os.path.join(self.memory_dir, "trades", f"{self.symbol}_trades.json")
        if not os.path.exists(trades_file):
            return []
        
        try:
            with open(trades_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载交易记录失败: {e}")
            return []
    
    def _save_trades(self):
        """保存交易记录"""
        trades_file = os.path.join(self.memory_dir, "trades", f"{self.symbol}_trades.json")
        try:
            with open(trades_file, "w") as f:
                json.dump(self.trades, f, indent=2)
            logger.info(f"已保存 {len(self.trades)} 条交易记录")
        except Exception as e:
            logger.error(f"保存交易记录失败: {e}")
    
    def _update_stats(self):
        """更新交易统计数据"""
        if not self.trades:
            self.stats = {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_profit": 0.0,
                "avg_loss": 0.0,
                "total_profit": 0.0,
                "max_profit": 0.0,
                "max_loss": 0.0,
                "profit_factor": 0.0
            }
            return
        
        # 计算基本统计数据
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.get("pnl", 0) > 0)
        losing_trades = sum(1 for t in self.trades if t.get("pnl", 0) < 0)
        
        # 避免除零错误
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # 计算盈亏统计
        profits = [t.get("pnl", 0) for t in self.trades if t.get("pnl", 0) > 0]
        losses = [t.get("pnl", 0) for t in self.trades if t.get("pnl", 0) < 0]
        
        avg_profit = np.mean(profits) if profits else 0
        avg_loss = np.mean(losses) if losses else 0
        total_profit = sum(profits) + sum(losses)
        
        # 最大盈亏
        max_profit = max(profits) if profits else 0
        max_loss = min(losses) if losses else 0
        
        # 盈亏比
        profit_factor = abs(sum(profits) / sum(losses)) if sum(losses) != 0 else float('inf')
        
        # 更新统计数据
        self.stats = {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "avg_profit": avg_profit,
            "avg_loss": avg_loss,
            "total_profit": total_profit,
            "max_profit": max_profit,
            "max_loss": max_loss,
            "profit_factor": profit_factor
        }
    
    def add_trade(self, trade_data: Dict) -> bool:
        """
        添加交易记录
        
        参数:
            trade_data: 交易数据字典，应包含以下字段:
                - symbol: 交易标的
                - entry_time: 入场时间
                - exit_time: 出场时间
                - entry_price: 入场价格
                - exit_price: 出场价格
                - direction: 交易方向 (LONG/SHORT)
                - quantity: 交易数量
                - pnl: 盈亏金额
                - pnl_percent: 盈亏百分比
                - entry_reason: 入场原因
                - exit_reason: 出场原因
                - market_condition: 市场状态描述
                - ai_signal: AI信号
                - ai_confidence: AI置信度
                可选字段:
                - strategy_name: 策略名称
                - stop_loss: 止损设置
                - take_profit: 止盈设置
                - tags: 标签列表
                - notes: 备注
                
        返回:
            是否成功添加
        """
        # 检查必要字段
        required_fields = ["symbol", "entry_time", "entry_price", "direction"]
        for field in required_fields:
            if field not in trade_data:
                logger.error(f"交易数据缺少必要字段: {field}")
                return False
        
        # 确保符号匹配
        if trade_data.get("symbol") != self.symbol:
            logger.warning(f"交易数据符号 {trade_data.get('symbol')} 与记忆库符号 {self.symbol} 不匹配")
        
        # 添加时间戳
        trade_data["timestamp"] = datetime.now().isoformat()
        
        # 添加交易ID
        trade_id = f"{self.symbol}_{len(self.trades) + 1}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        trade_data["trade_id"] = trade_id
        
        # 添加到交易列表
        self.trades.append(trade_data)
        
        # 保存交易记录
        self._save_trades()
        
        # 更新统计数据
        self._update_stats()
        
        logger.info(f"已添加新交易记录 ID: {trade_id}")
        return True
    
    def get_trades(self, 
                  start_date: Optional[str] = None, 
                  end_date: Optional[str] = None,
                  direction: Optional[str] = None,
                  outcome: Optional[str] = None,
                  limit: int = 100) -> List[Dict]:
        """
        获取交易记录
        
        参数:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            direction: 交易方向 (LONG/SHORT)
            outcome: 交易结果 (win/loss)
            limit: 最大返回数量
            
        返回:
            符合条件的交易记录列表
        """
        # 转换日期字符串为datetime对象
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.min
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.max
        
        # 过滤交易
        filtered_trades = []
        for trade in self.trades:
            # 过滤日期
            try:
                trade_dt = datetime.strptime(trade.get("entry_time", "").split("T")[0], "%Y-%m-%d")
                if trade_dt < start_dt or trade_dt > end_dt:
                    continue
            except (ValueError, AttributeError, IndexError):
                # 如果日期解析失败，尝试备用解析方式
                try:
                    trade_dt = datetime.strptime(trade.get("entry_time", "")[:10], "%Y-%m-%d")
                    if trade_dt < start_dt or trade_dt > end_dt:
                        continue
                except:
                    # 如果仍然失败，默认不过滤
                    pass
            
            # 过滤方向
            if direction and trade.get("direction", "").upper() != direction.upper():
                continue
            
            # 过滤结果
            if outcome:
                pnl = trade.get("pnl", 0)
                if outcome.lower() == "win" and pnl <= 0:
                    continue
                if outcome.lower() == "loss" and pnl >= 0:
                    continue
            
            filtered_trades.append(trade)
        
        # 按日期排序，最新的在前
        filtered_trades.sort(key=lambda x: x.get("entry_time", ""), reverse=True)
        
        # 限制返回数量
        return filtered_trades[:limit]
    
    def get_stats(self, 
                 start_date: Optional[str] = None, 
                 end_date: Optional[str] = None) -> Dict:
        """
        获取指定时间范围的交易统计
        
        参数:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        返回:
            统计数据字典
        """
        # 如果没有指定日期范围，返回全局统计
        if not start_date and not end_date:
            return self.stats
        
        # 获取指定日期范围的交易
        filtered_trades = self.get_trades(start_date=start_date, end_date=end_date, limit=10000)
        
        # 如果没有交易，返回空统计
        if not filtered_trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_profit": 0.0,
                "avg_loss": 0.0,
                "total_profit": 0.0,
                "max_profit": 0.0,
                "max_loss": 0.0,
                "profit_factor": 0.0
            }
        
        # 计算统计数据
        total_trades = len(filtered_trades)
        winning_trades = sum(1 for t in filtered_trades if t.get("pnl", 0) > 0)
        losing_trades = sum(1 for t in filtered_trades if t.get("pnl", 0) < 0)
        
        # 避免除零错误
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # 计算盈亏统计
        profits = [t.get("pnl", 0) for t in filtered_trades if t.get("pnl", 0) > 0]
        losses = [t.get("pnl", 0) for t in filtered_trades if t.get("pnl", 0) < 0]
        
        avg_profit = np.mean(profits) if profits else 0
        avg_loss = np.mean(losses) if losses else 0
        total_profit = sum(profits) + sum(losses)
        
        # 最大盈亏
        max_profit = max(profits) if profits else 0
        max_loss = min(losses) if losses else 0
        
        # 盈亏比
        profit_factor = abs(sum(profits) / sum(losses)) if sum(losses) != 0 else float('inf')
        
        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "avg_profit": avg_profit,
            "avg_loss": avg_loss,
            "total_profit": total_profit,
            "max_profit": max_profit,
            "max_loss": max_loss,
            "profit_factor": profit_factor
        }
    
    def export_to_csv(self, file_path: Optional[str] = None) -> str:
        """
        导出交易记录到CSV文件
        
        参数:
            file_path: 导出文件路径，默认为记忆库目录下的CSV文件
            
        返回:
            导出文件路径
        """
        if not self.trades:
            logger.warning("没有交易数据可供导出")
            return ""
        
        # 默认导出路径
        if not file_path:
            file_path = os.path.join(self.memory_dir, f"{self.symbol}_trades_export.csv")
        
        try:
            # 转换为DataFrame
            df = pd.DataFrame(self.trades)
            
            # 导出到CSV
            df.to_csv(file_path, index=False)
            logger.info(f"已导出 {len(self.trades)} 条交易记录到 {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"导出交易记录失败: {e}")
            return "" 