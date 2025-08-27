"""
市场数据模块 - 获取SPY及其期权链数据
支持多种数据源: yfinance, pandas-datareader, alpaca, polygon
"""
import logging
from typing import Dict, List, Optional, Union, Tuple

# 导入子模块
from utils.market_data_base import MarketDataSource
from utils.market_data_spy import SPYDataManager

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("market_data")

# 导出所有需要的类和函数，方便外部直接使用
__all__ = ['MarketDataSource', 'SPYDataManager', 'get_default_spy_manager']

# 创建默认的SPY数据管理器实例
_default_spy_manager = None

def get_default_spy_manager(data_source: str = "yfinance", 
                          cache_dir: str = "data/cache") -> SPYDataManager:
    """
    获取默认的SPY数据管理器
    如果已初始化，则返回现有实例；否则创建新实例
    
    参数:
        data_source: 数据源选择
        cache_dir: 缓存目录
        
    返回:
        SPY数据管理器实例
    """
    global _default_spy_manager
    if _default_spy_manager is None:
        _default_spy_manager = SPYDataManager(data_source, cache_dir)
    return _default_spy_manager

# 测试代码
if __name__ == "__main__":
    print("正在测试市场数据模块...")
    
    # 测试基础市场数据源
    data_source = MarketDataSource("yfinance")
    print(f"基础数据源就绪状态: {data_source.is_ready}")
    
    # 测试SPY数据管理器
    spy_manager = get_default_spy_manager()
    current_price = spy_manager.get_spy_price()
    print(f"SPY当前价格: ${current_price}")
    
    # 获取SPY历史数据
    spy_history = spy_manager.get_spy_history(interval="1d", period="1mo")
    if spy_history is not None:
        print(f"成功获取SPY历史数据，共{len(spy_history)}条记录")
    
    # 获取SPY期权到期日
    nearest_date = spy_manager.get_nearest_expiration()
    if nearest_date:
        print(f"最近的SPY期权到期日: {nearest_date}")
        
        # 获取期权数据
        option_data = spy_manager.get_spy_option_data(nearest_date)
        if option_data:
            # 计算期权指标
            metrics = spy_manager.calculate_option_metrics(option_data)
            print("\nSPY期权指标:")
            for key, value in metrics.items():
                print(f"{key}: {value}") 