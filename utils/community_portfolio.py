#!/usr/bin/env python
"""
社区组合池 & 策略管理模块
- 支持用户订阅组合
- 支持动态AI分析组合表现
- 支持组合自动群内推送
"""

import os
import json
import logging
import asyncio
import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import tempfile
import uuid

# 导入AI路由器
from utils.ai_router import AIRouter, AIRouterSync

logger = logging.getLogger(__name__)

class CommunityPortfolio:
    """
    社区组合池管理器
    用于管理多组合和用户订阅关系
    """
    
    def __init__(self, config: Dict = None):
        """
        初始化社区组合池
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self._load_config()
        self.ai_router = AIRouter()
        self.portfolios = {}  # 组合数据
        self.subscribers = {}  # 用户订阅关系
        self.vip_users = set()  # VIP用户
        self.performance_cache = {}  # 性能缓存
        self.last_update = {}  # 最后更新时间
        
        # 加载历史记录和订阅关系
        self._load_portfolios()
        self._load_subscribers()
        
    def _load_config(self):
        """从配置文件加载配置"""
        try:
            if not self.config:
                # 尝试加载社区版配置
                config_path = os.path.join("config", "warmachine_community_config.json")
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                        self.config = config.get("community_portfolio", {})
                else:
                    # 尝试从普通配置加载
                    config_path = os.path.join("config", "warmachine_config.json")
                    if os.path.exists(config_path):
                        with open(config_path, "r", encoding="utf-8") as f:
                            config = json.load(f)
                            self.config = config.get("community_portfolio", {})
            
            # 设置默认值
            self.data_dir = self.config.get("data_dir", "data/community")
            self.default_portfolios = self.config.get("default_portfolios", {
                "sp500_ai": {
                    "name": "SP500 AI策略",
                    "description": "基于大型股票AI筛选的多头策略",
                    "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN"],
                    "weights": [0.25, 0.25, 0.25, 0.25],
                    "is_public": True
                },
                "crypto_trend": {
                    "name": "加密货币趋势",
                    "description": "加密货币多头趋势跟踪策略",
                    "symbols": ["BTC-USD", "ETH-USD"],
                    "weights": [0.6, 0.4],
                    "is_public": True
                },
                "tech_momentum": {
                    "name": "科技动量策略",
                    "description": "高科技股票动量策略",
                    "symbols": ["NVDA", "AMD", "TSLA", "META"],
                    "weights": [0.3, 0.2, 0.3, 0.2],
                    "is_public": True
                },
                "vip_alpha": {
                    "name": "VIP Alpha策略",
                    "description": "仅VIP用户可见的高阿尔法策略",
                    "symbols": ["TSLA", "NVDA", "NFLX", "SHOP"],
                    "weights": [0.3, 0.3, 0.2, 0.2],
                    "is_public": False,
                    "vip_only": True
                }
            })
            
            # 确保数据目录存在
            os.makedirs(self.data_dir, exist_ok=True)
            os.makedirs(os.path.join(self.data_dir, "charts"), exist_ok=True)
            os.makedirs(os.path.join(self.data_dir, "portfolios"), exist_ok=True)
            os.makedirs(os.path.join(self.data_dir, "subscribers"), exist_ok=True)
            
            logger.info(f"社区组合池配置加载完成，默认组合数: {len(self.default_portfolios)}")
        except Exception as e:
            logger.error(f"加载社区组合池配置失败: {e}")
            self.data_dir = "data/community"
            self.default_portfolios = {}
            
            # 确保数据目录存在
            os.makedirs(self.data_dir, exist_ok=True)
            os.makedirs(os.path.join(self.data_dir, "charts"), exist_ok=True)
            os.makedirs(os.path.join(self.data_dir, "portfolios"), exist_ok=True)
            os.makedirs(os.path.join(self.data_dir, "subscribers"), exist_ok=True)
    
    def _load_portfolios(self):
        """加载组合数据"""
        try:
            portfolios_file = os.path.join(self.data_dir, "portfolios", "portfolios.json")
            if os.path.exists(portfolios_file):
                with open(portfolios_file, "r", encoding="utf-8") as f:
                    self.portfolios = json.load(f)
                logger.info(f"已加载组合数据, 组合数: {len(self.portfolios)}")
            else:
                # 使用默认组合
                self.portfolios = self.default_portfolios
                self._save_portfolios()
                logger.info(f"使用默认组合数据, 组合数: {len(self.portfolios)}")
        except Exception as e:
            logger.error(f"加载组合数据失败: {e}")
            # 使用默认组合
            self.portfolios = self.default_portfolios
            self._save_portfolios()
    
    def _save_portfolios(self):
        """保存组合数据"""
        try:
            portfolios_file = os.path.join(self.data_dir, "portfolios", "portfolios.json")
            with open(portfolios_file, "w", encoding="utf-8") as f:
                json.dump(self.portfolios, f, ensure_ascii=False, indent=2)
            logger.info("组合数据已保存")
        except Exception as e:
            logger.error(f"保存组合数据失败: {e}")
    
    def _load_subscribers(self):
        """加载用户订阅关系"""
        try:
            subscribers_file = os.path.join(self.data_dir, "subscribers", "subscribers.json")
            if os.path.exists(subscribers_file):
                with open(subscribers_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.subscribers = data.get("subscribers", {})
                    self.vip_users = set(data.get("vip_users", []))
                logger.info(f"已加载订阅数据, 订阅用户数: {len(self.subscribers)}")
            else:
                self._save_subscribers()
                logger.info("创建了空的订阅数据")
        except Exception as e:
            logger.error(f"加载订阅数据失败: {e}")
            self._save_subscribers()
    
    def _save_subscribers(self):
        """保存用户订阅关系"""
        try:
            subscribers_file = os.path.join(self.data_dir, "subscribers", "subscribers.json")
            with open(subscribers_file, "w", encoding="utf-8") as f:
                data = {
                    "subscribers": self.subscribers,
                    "vip_users": list(self.vip_users)
                }
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("订阅数据已保存")
        except Exception as e:
            logger.error(f"保存订阅数据失败: {e}")
    
    def get_portfolio_list(self, user_id: str = None) -> List[Dict]:
        """
        获取组合列表
        
        Args:
            user_id: 用户ID，用于过滤VIP组合
            
        Returns:
            组合列表
        """
        result = []
        is_vip = user_id in self.vip_users
        
        for portfolio_id, portfolio in self.portfolios.items():
            # 检查VIP可见性
            if portfolio.get("vip_only", False) and not is_vip:
                continue
                
            # 检查公开可见性
            if not portfolio.get("is_public", True) and (not user_id or user_id not in self.subscribers.get(portfolio_id, [])):
                continue
                
            result.append({
                "id": portfolio_id,
                "name": portfolio.get("name", "未命名组合"),
                "description": portfolio.get("description", ""),
                "symbols": portfolio.get("symbols", []),
                "is_subscribed": user_id in self.subscribers.get(portfolio_id, []) if user_id else False,
                "vip_only": portfolio.get("vip_only", False)
            })
        
        return result
    
    def get_portfolio(self, portfolio_id: str) -> Optional[Dict]:
        """
        获取单个组合详情
        
        Args:
            portfolio_id: 组合ID
            
        Returns:
            组合详情，若不存在则返回None
        """
        return self.portfolios.get(portfolio_id)
    
    def create_portfolio(self, portfolio_data: Dict) -> str:
        """
        创建新组合
        
        Args:
            portfolio_data: 组合数据
            
        Returns:
            新组合ID
        """
        # 生成ID
        portfolio_id = portfolio_data.get("id", f"portfolio_{str(uuid.uuid4())[:8]}")
        
        # 标准化数据
        if "weights" not in portfolio_data and "symbols" in portfolio_data:
            # 自动平均分配权重
            symbols_count = len(portfolio_data["symbols"])
            portfolio_data["weights"] = [1.0 / symbols_count] * symbols_count
        
        # 确保必要字段存在
        if "name" not in portfolio_data:
            portfolio_data["name"] = f"组合 {portfolio_id}"
        
        if "is_public" not in portfolio_data:
            portfolio_data["is_public"] = True
        
        # 添加组合
        self.portfolios[portfolio_id] = portfolio_data
        
        # 保存到文件
        self._save_portfolios()
        
        logger.info(f"创建了新组合: {portfolio_id}")
        return portfolio_id
    
    def update_portfolio(self, portfolio_id: str, portfolio_data: Dict) -> bool:
        """
        更新组合
        
        Args:
            portfolio_id: 组合ID
            portfolio_data: 更新的组合数据
            
        Returns:
            更新是否成功
        """
        if portfolio_id not in self.portfolios:
            logger.warning(f"尝试更新不存在的组合: {portfolio_id}")
            return False
        
        # 更新组合数据
        current_data = self.portfolios[portfolio_id]
        current_data.update(portfolio_data)
        self.portfolios[portfolio_id] = current_data
        
        # 保存到文件
        self._save_portfolios()
        
        logger.info(f"更新了组合: {portfolio_id}")
        return True
    
    def delete_portfolio(self, portfolio_id: str) -> bool:
        """
        删除组合
        
        Args:
            portfolio_id: 组合ID
            
        Returns:
            删除是否成功
        """
        if portfolio_id not in self.portfolios:
            logger.warning(f"尝试删除不存在的组合: {portfolio_id}")
            return False
        
        # 删除组合
        del self.portfolios[portfolio_id]
        
        # 删除相关的订阅
        if portfolio_id in self.subscribers:
            del self.subscribers[portfolio_id]
        
        # 保存到文件
        self._save_portfolios()
        self._save_subscribers()
        
        logger.info(f"删除了组合: {portfolio_id}")
        return True
    
    def subscribe_portfolio(self, user_id: str, portfolio_id: str) -> bool:
        """
        用户订阅组合
        
        Args:
            user_id: 用户ID
            portfolio_id: 组合ID
            
        Returns:
            订阅是否成功
        """
        if portfolio_id not in self.portfolios:
            logger.warning(f"尝试订阅不存在的组合: {portfolio_id}")
            return False
        
        # 检查VIP限制
        portfolio = self.portfolios[portfolio_id]
        if portfolio.get("vip_only", False) and user_id not in self.vip_users:
            logger.warning(f"非VIP用户 {user_id} 尝试订阅VIP组合: {portfolio_id}")
            return False
        
        # 添加订阅
        if portfolio_id not in self.subscribers:
            self.subscribers[portfolio_id] = []
        
        if user_id not in self.subscribers[portfolio_id]:
            self.subscribers[portfolio_id].append(user_id)
            
            # 保存到文件
            self._save_subscribers()
            
            logger.info(f"用户 {user_id} 订阅了组合: {portfolio_id}")
            return True
        else:
            logger.info(f"用户 {user_id} 已经订阅了组合: {portfolio_id}")
            return True
    
    def unsubscribe_portfolio(self, user_id: str, portfolio_id: str) -> bool:
        """
        用户取消订阅组合
        
        Args:
            user_id: 用户ID
            portfolio_id: 组合ID
            
        Returns:
            取消订阅是否成功
        """
        if portfolio_id not in self.subscribers or user_id not in self.subscribers[portfolio_id]:
            logger.warning(f"用户 {user_id} 尝试取消未订阅的组合: {portfolio_id}")
            return False
        
        # 移除订阅
        self.subscribers[portfolio_id].remove(user_id)
        
        # 保存到文件
        self._save_subscribers()
        
        logger.info(f"用户 {user_id} 取消订阅了组合: {portfolio_id}")
        return True
    
    def get_user_subscriptions(self, user_id: str) -> List[str]:
        """
        获取用户的所有订阅组合ID
        
        Args:
            user_id: 用户ID
            
        Returns:
            组合ID列表
        """
        subscriptions = []
        for portfolio_id, subscribers in self.subscribers.items():
            if user_id in subscribers:
                subscriptions.append(portfolio_id)
        return subscriptions
    
    def add_vip_user(self, user_id: str) -> bool:
        """
        添加VIP用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            添加是否成功
        """
        if user_id in self.vip_users:
            logger.info(f"用户 {user_id} 已经是VIP")
            return True
        
        self.vip_users.add(user_id)
        self._save_subscribers()
        
        logger.info(f"将用户 {user_id} 添加为VIP")
        return True
    
    def remove_vip_user(self, user_id: str) -> bool:
        """
        移除VIP用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            移除是否成功
        """
        if user_id not in self.vip_users:
            logger.warning(f"尝试移除不是VIP的用户: {user_id}")
            return False
        
        self.vip_users.remove(user_id)
        self._save_subscribers()
        
        logger.info(f"将用户 {user_id} 从VIP移除")
        return True
    
    def is_vip_user(self, user_id: str) -> bool:
        """
        检查是否为VIP用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否为VIP用户
        """
        return user_id in self.vip_users
    
    async def generate_portfolio_chart(self, portfolio_id: str, days: int = 30) -> Optional[str]:
        """
        生成组合绩效图表
        
        Args:
            portfolio_id: 组合ID
            days: 回溯天数
            
        Returns:
            生成的图表文件路径，若失败则返回None
        """
        if portfolio_id not in self.portfolios:
            logger.warning(f"尝试生成不存在的组合图表: {portfolio_id}")
            return None
        
        portfolio = self.portfolios[portfolio_id]
        name = portfolio.get("name", "未命名组合")
        symbols = portfolio.get("symbols", [])
        weights = portfolio.get("weights", [1.0 / len(symbols)] * len(symbols))
        
        if not symbols:
            logger.warning(f"组合 {portfolio_id} 没有股票")
            return None
        
        try:
            # 模拟历史数据
            # 在实际项目中，这里应该从数据库或API获取真实数据
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=days)
            date_range = pd.date_range(start=start_date, end=end_date)
            
            # 创建随机涨跌的价格数据
            np.random.seed(42)  # 确保可重现性
            price_data = {}
            for symbol in symbols:
                # 生成基础价格
                base_price = 100 + np.random.rand() * 100
                daily_returns = np.random.normal(0.0005, 0.015, len(date_range))
                prices = [base_price]
                
                for ret in daily_returns:
                    prices.append(prices[-1] * (1 + ret))
                
                price_data[symbol] = pd.Series(prices[:-1], index=date_range)
            
            df = pd.DataFrame(price_data)
            
            # 计算组合价值
            portfolio_value = pd.Series(0.0, index=date_range)
            for symbol, weight in zip(symbols, weights):
                normalized = df[symbol] / df[symbol].iloc[0]
                portfolio_value += normalized * weight
            
            # 计算关键指标
            daily_returns = portfolio_value.pct_change().dropna()
            cumulative_returns = (portfolio_value / portfolio_value.iloc[0]) - 1
            
            sharpe = np.sqrt(252) * daily_returns.mean() / daily_returns.std()
            max_drawdown = (portfolio_value / portfolio_value.cummax() - 1).min()
            total_return = cumulative_returns.iloc[-1]
            volatility = daily_returns.std() * np.sqrt(252)
            
            # 创建图表
            plt.figure(figsize=(10, 6))
            plt.plot(cumulative_returns.index, cumulative_returns * 100, 'b-')
            plt.title(f"{name} - 组合表现 (近{days}天)")
            plt.fill_between(cumulative_returns.index, cumulative_returns * 100, 0, 
                             where=(cumulative_returns > 0), facecolor='green', alpha=0.2)
            plt.fill_between(cumulative_returns.index, cumulative_returns * 100, 0, 
                             where=(cumulative_returns < 0), facecolor='red', alpha=0.2)
            plt.axhline(y=0, color='k', linestyle='-', alpha=0.2)
            plt.grid(True, alpha=0.3)
            plt.ylabel('累计回报率 (%)')
            
            # 添加指标标注
            plt.figtext(0.15, 0.05, f"总回报率: {total_return:.2%}", ha="left")
            plt.figtext(0.35, 0.05, f"Sharpe比率: {sharpe:.2f}", ha="left")
            plt.figtext(0.55, 0.05, f"最大回撤: {max_drawdown:.2%}", ha="left")
            plt.figtext(0.75, 0.05, f"波动率: {volatility:.2%}", ha="left")
            
            # 保存图表
            chart_filename = f"portfolio_{portfolio_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            chart_path = os.path.join(self.data_dir, "charts", chart_filename)
            plt.savefig(chart_path, dpi=100, bbox_inches='tight')
            plt.close()
            
            logger.info(f"为组合 {portfolio_id} 生成了图表: {chart_path}")
            
            # 更新性能缓存
            self.performance_cache[portfolio_id] = {
                "total_return": total_return,
                "sharpe": sharpe,
                "max_drawdown": max_drawdown,
                "volatility": volatility,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            return chart_path
        except Exception as e:
            logger.error(f"生成组合 {portfolio_id} 图表失败: {e}")
            return None
    
    async def analyze_portfolio(self, portfolio_id: str) -> Dict:
        """
        使用AI分析组合
        
        Args:
            portfolio_id: 组合ID
            
        Returns:
            分析结果
        """
        if portfolio_id not in self.portfolios:
            logger.warning(f"尝试分析不存在的组合: {portfolio_id}")
            return {"error": "组合不存在"}
        
        portfolio = self.portfolios[portfolio_id]
        name = portfolio.get("name", "未命名组合")
        symbols = portfolio.get("symbols", [])
        
        if not symbols:
            logger.warning(f"组合 {portfolio_id} 没有股票")
            return {"error": "组合不包含任何股票"}
        
        # 使用缓存的性能数据，如果可用
        perf_data = self.performance_cache.get(portfolio_id, {})
        
        try:
            # 构建提示词
            prompt = f"""
请作为专业量化交易分析师，对以下投资组合进行简短分析(200字以内)。
给出对当前市场环境下的风险评估和未来走势预测:

组合名称: {name}
组合成分: {', '.join(symbols)}
历史表现:
- 总回报率: {perf_data.get('total_return', '未知')}
- Sharpe比率: {perf_data.get('sharpe', '未知')}
- 最大回撤: {perf_data.get('max_drawdown', '未知')}
- 波动率: {perf_data.get('volatility', '未知')}

分析重点:
1. 组合风险水平
2. 当前市场环境下的优势和劣势
3. 未来1-2周的预期表现
4. 任何需要注意的风险因素
            """
            
            # 调用AI获取分析
            analysis = await self.ai_router.ask(prompt)
            
            result = {
                "portfolio_id": portfolio_id,
                "name": name,
                "symbols": symbols,
                "analysis": analysis,
                "performance": perf_data,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            logger.info(f"完成组合 {portfolio_id} 的AI分析")
            return result
        except Exception as e:
            logger.error(f"分析组合 {portfolio_id} 失败: {e}")
            return {"error": f"分析失败: {str(e)}"}
    
    async def get_portfolio_updates(self, user_id: str = None) -> List[Dict]:
        """
        获取组合更新
        用于定期推送
        
        Args:
            user_id: 如果提供，则只返回特定用户订阅的组合
            
        Returns:
            组合更新列表
        """
        updates = []
        
        # 确定要处理的组合
        portfolios_to_process = []
        if user_id:
            # 获取用户订阅的组合
            for portfolio_id in self.get_user_subscriptions(user_id):
                if portfolio_id in self.portfolios:
                    portfolios_to_process.append((portfolio_id, self.portfolios[portfolio_id]))
        else:
            # 处理所有组合
            portfolios_to_process = list(self.portfolios.items())
        
        # 生成每个组合的更新
        for portfolio_id, portfolio in portfolios_to_process:
            # 检查是否需要更新
            last_update_time = self.last_update.get(portfolio_id, datetime.datetime.min)
            current_time = datetime.datetime.now()
            
            # 如果距离上次更新超过6小时，生成新的分析
            if (current_time - last_update_time).total_seconds() > 6 * 3600:
                # 生成图表
                chart_path = await self.generate_portfolio_chart(portfolio_id)
                
                # 获取AI分析
                analysis = await self.analyze_portfolio(portfolio_id)
                
                updates.append({
                    "portfolio_id": portfolio_id,
                    "name": portfolio.get("name", "未命名组合"),
                    "analysis": analysis.get("analysis", "分析未能生成"),
                    "chart_path": chart_path,
                    "performance": analysis.get("performance", {}),
                    "timestamp": current_time.isoformat()
                })
                
                # 更新最后更新时间
                self.last_update[portfolio_id] = current_time
        
        return updates

# 同步接口包装
class CommunityPortfolioSync:
    """CommunityPortfolio的同步接口包装器"""
    
    def __init__(self, config: Dict = None):
        self.portfolio = CommunityPortfolio(config)
        self.loop = asyncio.get_event_loop()
    
    def generate_portfolio_chart(self, portfolio_id: str, days: int = 30) -> Optional[str]:
        """同步调用generate_portfolio_chart"""
        return self.loop.run_until_complete(
            self.portfolio.generate_portfolio_chart(portfolio_id, days)
        )
    
    def analyze_portfolio(self, portfolio_id: str) -> Dict:
        """同步调用analyze_portfolio"""
        return self.loop.run_until_complete(
            self.portfolio.analyze_portfolio(portfolio_id)
        )
    
    def get_portfolio_updates(self, user_id: str = None) -> List[Dict]:
        """同步调用get_portfolio_updates"""
        return self.loop.run_until_complete(
            self.portfolio.get_portfolio_updates(user_id)
        )

# 示例用法
async def example():
    portfolio_manager = CommunityPortfolio()
    
    # 创建一个新的组合
    portfolio_data = {
        "name": "测试组合",
        "description": "测试用的组合",
        "symbols": ["AAPL", "MSFT", "GOOGL"],
        "is_public": True
    }
    portfolio_id = portfolio_manager.create_portfolio(portfolio_data)
    
    # 订阅组合
    portfolio_manager.subscribe_portfolio("user123", portfolio_id)
    
    # 生成图表
    chart_path = await portfolio_manager.generate_portfolio_chart(portfolio_id)
    print(f"图表路径: {chart_path}")
    
    # 分析组合
    analysis = await portfolio_manager.analyze_portfolio(portfolio_id)
    print(f"分析结果: {analysis}")
    
    # 获取更新
    updates = await portfolio_manager.get_portfolio_updates("user123")
    print(f"更新数量: {len(updates)}")

# 直接运行测试
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example()) 