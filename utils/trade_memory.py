"""
交易记忆库主模块 - 集成核心、分析和可视化功能
AI量化系统6.0 - 交易记忆与自学习闭环的整合组件
"""
import os
import logging
from typing import Dict, List, Optional, Union, Tuple

# 导入子模块
from utils.trade_memory_core import TradeMemory
from utils.trade_memory_analysis import TradeAnalyzer
from utils.trade_memory_visualization import TradeVisualizer

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("trade_memory")

class TradeMemorySystem:
    """
    交易记忆系统 - 整合核心、分析和可视化功能的完整系统
    """
    
    def __init__(self, memory_dir: str = "data/trade_memory", 
                 symbol: str = "SPY"):
        """
        初始化交易记忆系统
        
        参数:
            memory_dir: 记忆库存储目录
            symbol: 交易标的代码
        """
        self.memory_dir = memory_dir
        self.symbol = symbol
        
        # 初始化核心组件
        self.core = TradeMemory(memory_dir, symbol)
        
        # 初始化分析组件
        self.analyzer = TradeAnalyzer(memory_dir, symbol, self.core.trades)
        
        # 初始化可视化组件
        self.visualizer = TradeVisualizer(memory_dir, symbol)
        
        logger.info(f"已初始化 {symbol} 交易记忆系统，加载 {len(self.core.trades)} 条交易记录")
    
    def add_trade(self, trade_data: Dict) -> bool:
        """
        添加交易记录
        
        参数:
            trade_data: 交易数据字典
                
        返回:
            是否成功添加
        """
        # 使用核心组件添加交易
        success = self.core.add_trade(trade_data)
        
        # 更新分析器的交易数据
        if success:
            self.analyzer.trades = self.core.trades
        
        return success
    
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
        return self.core.get_trades(start_date, end_date, direction, outcome, limit)
    
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
        return self.core.get_stats(start_date, end_date)
    
    def analyze_patterns(self,
                        pattern_type: str = "all",
                        min_occurrences: int = 3) -> List[Dict]:
        """
        分析交易模式
        
        参数:
            pattern_type: 模式类型 ("failure", "success", "all")
            min_occurrences: 最小出现次数
            
        返回:
            识别的模式列表
        """
        return self.analyzer.analyze_trade_patterns(pattern_type, min_occurrences)
    
    def get_common_patterns(self,
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
        return self.analyzer.get_most_common_patterns(pattern_type, limit)
    
    def generate_prompt_context(self, trade_type: str = "option") -> str:
        """
        生成包含历史交易经验的提示词上下文
        
        参数:
            trade_type: 交易类型 ("option", "stock", "futures")
            
        返回:
            历史经验提示词上下文
        """
        stats = self.core.get_stats()
        return self.analyzer.generate_historical_prompt_context(trade_type, stats)
    
    def visualize_trades(self,
                        start_date: Optional[str] = None, 
                        end_date: Optional[str] = None) -> str:
        """
        可视化交易历史
        
        参数:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        返回:
            保存的图表路径
        """
        trades = self.get_trades(start_date, end_date, limit=1000)
        return self.visualizer.visualize_trades(trades, start_date, end_date)
    
    def create_dashboard(self) -> str:
        """
        创建交易仪表盘
        
        返回:
            保存的仪表盘路径
        """
        trades = self.get_trades(limit=1000)
        return self.visualizer.create_performance_dashboard(trades)
    
    def analyze_by_factor(self) -> str:
        """
        按因素分析交易
        
        返回:
            保存的分析图表路径
        """
        trades = self.get_trades(limit=1000)
        return self.visualizer.plot_trade_analysis(trades, plot_type="by_factor")
    
    def export_to_csv(self, file_path: Optional[str] = None) -> str:
        """
        导出交易记录到CSV文件
        
        参数:
            file_path: 导出文件路径
            
        返回:
            导出文件路径
        """
        return self.core.export_to_csv(file_path)

# 测试代码
if __name__ == "__main__":
    # 创建交易记忆系统
    memory_system = TradeMemorySystem(memory_dir="data/test_trade_memory", symbol="SPY")
    
    # 添加一些测试交易记录
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
    
    # 添加测试交易
    for trade in test_trades:
        memory_system.add_trade(trade)
    
    # 打印统计信息
    print("===== 交易统计 =====")
    stats = memory_system.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # 分析交易模式
    print("\n===== 失败交易模式 =====")
    failure_patterns = memory_system.get_common_patterns(pattern_type="failure")
    for pattern in failure_patterns:
        print(f"模式: {pattern['pattern_type']} - {pattern['value']}")
        print(f"出现次数: {pattern['occurrences']}")
        print(f"平均盈亏: ${pattern['avg_pnl']:.2f}")
        print()
    
    # 测试历史经验提示词生成
    print("\n===== 历史经验提示词上下文 =====")
    context = memory_system.generate_prompt_context()
    print(context)
    
    # 可视化交易
    print("\n===== 生成交易可视化 =====")
    viz_path = memory_system.visualize_trades()
    print(f"可视化保存路径: {viz_path}")
    
    # 创建仪表盘
    print("\n===== 创建交易仪表盘 =====")
    dashboard_path = memory_system.create_dashboard()
    print(f"仪表盘保存路径: {dashboard_path}")
    
    # 导出到CSV
    print("\n===== 导出交易记录到CSV =====")
    csv_path = memory_system.export_to_csv()
    print(f"CSV导出路径: {csv_path}") 