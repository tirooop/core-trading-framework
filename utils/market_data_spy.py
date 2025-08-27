"""
SPY市场数据模块 - 专门处理SPY ETF及其期权数据
基于市场数据基类，实现针对SPY的缓存和分析逻辑
"""
import os
import json
import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Union, Tuple

# 导入基类
from utils.market_data_base import MarketDataSource

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("market_data_spy")

class SPYDataManager:
    """SPY数据管理器，专门处理SPY及其期权数据"""
    
    def __init__(self, data_source: str = "yfinance", cache_dir: str = "data/cache"):
        """
        初始化SPY数据管理器
        
        参数:
            data_source: 数据源选择
            cache_dir: 缓存目录
        """
        self.data_source = MarketDataSource(data_source)
        self.cache_dir = cache_dir
        
        # 创建缓存目录
        os.makedirs(cache_dir, exist_ok=True)
        
        # 缓存数据
        self.price_cache = {}
        self.history_cache = {}
        self.option_chain_cache = {}
        
        # 上次更新时间
        self.last_update_time = {}
    
    def get_spy_price(self) -> Optional[float]:
        """获取SPY当前价格"""
        return self.data_source.get_current_price("SPY")
    
    def get_spy_history(self, interval: str = "1d", period: str = "1mo", 
                       force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """
        获取SPY历史数据
        
        参数:
            interval: 时间间隔
            period: 时间跨度
            force_refresh: 是否强制刷新缓存
            
        返回:
            SPY历史数据
        """
        cache_key = f"SPY_{interval}_{period}"
        
        # 检查缓存是否过期
        current_time = datetime.now()
        if not force_refresh and cache_key in self.history_cache:
            last_update = self.last_update_time.get(cache_key, datetime.min)
            
            # 根据interval设置缓存过期时间
            if interval == "1m" and (current_time - last_update).seconds > 60:
                # 1分钟数据，1分钟过期
                force_refresh = True
            elif interval == "5m" and (current_time - last_update).seconds > 300:
                # 5分钟数据，5分钟过期
                force_refresh = True
            elif interval == "1h" and (current_time - last_update).seconds > 3600:
                # 小时数据，1小时过期
                force_refresh = True
            elif interval == "1d" and (current_time - last_update).days > 0:
                # 日线数据，1天过期
                force_refresh = True
        
        # 如果缓存有效，则返回缓存数据
        if not force_refresh and cache_key in self.history_cache:
            return self.history_cache[cache_key]
        
        # 获取新数据
        data = self.data_source.get_historical_data("SPY", interval, period)
        if data is not None:
            self.history_cache[cache_key] = data
            self.last_update_time[cache_key] = current_time
            
            # 保存到本地缓存
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.csv")
            data.to_csv(cache_file)
            logger.info(f"已更新 SPY {interval} 历史数据，保存到 {cache_file}")
        
        return data
    
    def get_spy_option_chain(self, force_refresh: bool = False) -> Optional[List[str]]:
        """
        获取SPY期权链可用的到期日
        
        参数:
            force_refresh: 是否强制刷新缓存
            
        返回:
            可用到期日列表
        """
        cache_key = "SPY_option_chain"
        
        # 检查缓存
        current_time = datetime.now()
        if not force_refresh and cache_key in self.option_chain_cache:
            last_update = self.last_update_time.get(cache_key, datetime.min)
            
            # 期权链数据，1天过期
            if (current_time - last_update).days <= 0:
                return self.option_chain_cache[cache_key]
        
        # 获取新数据
        options = self.data_source.get_option_chain("SPY")
        if options is not None:
            self.option_chain_cache[cache_key] = options
            self.last_update_time[cache_key] = current_time
            
            # 保存到本地缓存
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            try:
                with open(cache_file, 'w') as f:
                    json.dump(options, f)
                logger.info(f"已更新 SPY 期权链数据，保存到 {cache_file}")
            except Exception as e:
                logger.error(f"保存期权链数据失败: {e}")
        
        return options
    
    def get_spy_option_data(self, expiration_date: str, 
                           force_refresh: bool = False) -> Optional[Dict]:
        """
        获取SPY特定到期日的期权数据
        
        参数:
            expiration_date: 到期日 (YYYY-MM-DD)
            force_refresh: 是否强制刷新缓存
            
        返回:
            期权数据字典
        """
        cache_key = f"SPY_option_{expiration_date}"
        
        # 检查缓存
        current_time = datetime.now()
        if not force_refresh and cache_key in self.option_chain_cache:
            last_update = self.last_update_time.get(cache_key, datetime.min)
            
            # 期权数据，4小时过期
            if (current_time - last_update).seconds <= 14400:
                return self.option_chain_cache[cache_key]
        
        # 获取新数据
        option_data = self.data_source.get_option_data("SPY", expiration_date)
        if option_data is not None:
            self.option_chain_cache[cache_key] = option_data
            self.last_update_time[cache_key] = current_time
            
            # 保存到本地缓存 (这里数据结构可能较复杂，使用pickle)
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(option_data, f)
                logger.info(f"已更新 SPY {expiration_date} 期权数据，保存到 {cache_file}")
            except Exception as e:
                logger.error(f"保存期权数据失败: {e}")
        
        return option_data
    
    def calculate_option_metrics(self, option_data: Dict) -> Dict:
        """
        计算期权相关指标
        
        参数:
            option_data: 期权数据字典
            
        返回:
            计算的指标字典
        """
        metrics = {}
        
        try:
            if not option_data or 'calls' not in option_data or 'puts' not in option_data:
                return metrics
            
            calls = option_data['calls']
            puts = option_data['puts']
            
            # 计算看涨/看跌期权比率 (PCR)
            call_volume = calls['volume'].sum() if 'volume' in calls else 0
            put_volume = puts['volume'].sum() if 'volume' in puts else 0
            
            # 避免除零错误
            if call_volume > 0:
                pcr = put_volume / call_volume
            else:
                pcr = 0
                
            metrics['put_call_ratio'] = pcr
            
            # 计算隐含波动率均值
            if 'impliedVolatility' in calls:
                calls_iv_mean = calls['impliedVolatility'].mean()
                metrics['calls_iv_mean'] = calls_iv_mean
            
            if 'impliedVolatility' in puts:
                puts_iv_mean = puts['impliedVolatility'].mean()
                metrics['puts_iv_mean'] = puts_iv_mean
            
            # 计算价内期权数量
            if 'inTheMoney' in calls:
                itm_calls = calls[calls['inTheMoney'] == True].shape[0]
                metrics['itm_calls'] = itm_calls
            
            if 'inTheMoney' in puts:
                itm_puts = puts[puts['inTheMoney'] == True].shape[0]
                metrics['itm_puts'] = itm_puts
            
            # 计算未平衡指标
            metrics['call_put_imbalance'] = call_volume - put_volume
            
            # 计算价内/价外比率
            if 'inTheMoney' in calls and 'inTheMoney' in puts:
                otm_calls = calls[calls['inTheMoney'] == False].shape[0]
                otm_puts = puts[puts['inTheMoney'] == False].shape[0]
                
                if otm_calls > 0:
                    metrics['itm_otm_calls_ratio'] = itm_calls / otm_calls
                
                if otm_puts > 0:
                    metrics['itm_otm_puts_ratio'] = itm_puts / otm_puts
        
        except Exception as e:
            logger.error(f"计算期权指标失败: {e}")
        
        return metrics
    
    def get_nearest_expiration(self) -> Optional[str]:
        """
        获取最近的期权到期日
        
        返回:
            最近的到期日 (YYYY-MM-DD)，获取失败返回None
        """
        option_chain = self.get_spy_option_chain()
        if not option_chain:
            return None
        
        # 获取今天的日期
        today = datetime.now().date()
        
        # 找到今天以后最近的到期日
        nearest_date = None
        min_days = float('inf')
        
        for date_str in option_chain:
            try:
                expiry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                days_remaining = (expiry_date - today).days
                
                # 只考虑未到期的
                if days_remaining >= 0 and days_remaining < min_days:
                    min_days = days_remaining
                    nearest_date = date_str
            except ValueError:
                # 日期格式可能不同，跳过
                continue
        
        return nearest_date

# 测试代码
if __name__ == "__main__":
    # 测试SPY数据管理器
    spy_manager = SPYDataManager(data_source="yfinance")
    
    # 获取当前价格
    current_price = spy_manager.get_spy_price()
    print(f"SPY当前价格: ${current_price}")
    
    # 获取历史数据
    daily_data = spy_manager.get_spy_history(interval="1d", period="1mo")
    print("\nSPY日线数据:")
    print(daily_data.tail())
    
    # 获取期权链
    options = spy_manager.get_spy_option_chain()
    if options:
        print("\nSPY可用期权到期日:")
        print(options)
        
        # 获取最近到期日
        nearest_date = spy_manager.get_nearest_expiration()
        print(f"\n最近的期权到期日: {nearest_date}")
        
        # 获取期权数据
        if nearest_date:
            option_data = spy_manager.get_spy_option_data(nearest_date)
            if option_data and hasattr(option_data, 'calls') and hasattr(option_data, 'puts'):
                print("\n看涨期权数据:")
                print(option_data.calls.head())
                
                print("\n看跌期权数据:")
                print(option_data.puts.head())
                
                # 计算期权指标
                metrics = spy_manager.calculate_option_metrics(option_data)
                print("\n期权指标:")
                for key, value in metrics.items():
                    print(f"{key}: {value}") 