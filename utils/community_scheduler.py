#!/usr/bin/env python
"""
社区自动Routine调度模块
- 开盘前、盘中、收盘、夜间自动群内汇报
- 市场异动、鲸鱼流、组合池动态播报
"""

import os
import sys
import json
import time
import asyncio
import datetime
import logging
import random
import threading
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Callable
from queue import Queue
import pytz

# 导入相关模块
try:
    from utils.ai_router import AIRouter, AIRouterSync
    from utils.community_portfolio import CommunityPortfolio, CommunityPortfolioSync
except ImportError:
    # 开发环境兼容导入
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.ai_router import AIRouter, AIRouterSync
    from utils.community_portfolio import CommunityPortfolio, CommunityPortfolioSync

logger = logging.getLogger(__name__)

class CommunityScheduler:
    """
    社区自动Routine调度器
    用于定时执行任务并推送到社区
    """
    
    def __init__(self, config: Dict = None, notifier = None):
        """
        初始化调度器
        
        Args:
            config: 配置字典
            notifier: 通知模块，用于发送消息
        """
        self.config = config or {}
        self._load_config()
        
        # 通知器，用于发送消息
        self.notifier = notifier
        
        # AI路由器
        self.ai_router = AIRouterSync()
        
        # 组合管理器
        self.portfolio_manager = CommunityPortfolioSync()
        
        # 当前状态
        self.running = False
        self.market_open = False
        self.last_execution = {}
        self.next_execution = {}
        
        # 任务队列
        self.event_queue = Queue()
        
        # 调度器线程
        self.scheduler_thread = None
        self.event_thread = None
        
        # 初始化调度时间
        self._init_schedule()
        
        logger.info("社区调度器初始化完成")
    
    def _load_config(self):
        """从配置文件加载配置"""
        try:
            if not self.config:
                # 尝试加载社区版配置
                config_path = os.path.join("config", "warmachine_community_config.json")
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                        self.config = config.get("community_scheduler", {})
                else:
                    # 尝试从普通配置加载
                    config_path = os.path.join("config", "warmachine_config.json")
                    if os.path.exists(config_path):
                        with open(config_path, "r", encoding="utf-8") as f:
                            config = json.load(f)
                            self.config = config.get("community_scheduler", {})
            
            # 设置默认值
            self.enabled = self.config.get("enabled", True)
            self.timezone = pytz.timezone(self.config.get("timezone", "America/New_York"))
            
            # 任务时间
            self.schedule_config = self.config.get("schedule", {
                "pre_market": {"enabled": True, "time": "09:00"},
                "market_open": {"enabled": True, "time": "09:30"},
                "mid_day": {"enabled": True, "time": "12:30"},
                "market_close": {"enabled": True, "time": "16:00"},
                "after_hours": {"enabled": True, "time": "16:30"},
                "evening": {"enabled": True, "time": "20:00"}
            })
            
            # 特殊时间定义
            market_hours = self.config.get("market_hours", {
                "open": "09:30",
                "close": "16:00",
                "timezone": "America/New_York"
            })
            
            self.market_open_time = self._parse_time(market_hours.get("open", "09:30"))
            self.market_close_time = self._parse_time(market_hours.get("close", "16:00"))
            
            # 实时监控配置
            self.realtime_config = self.config.get("realtime", {
                "enabled": True,
                "whale_alert": True,
                "whale_threshold": 5000000,  # $5M交易预警
                "volatility_alert": True,
                "volatility_threshold": 3.0,  # 3%波动预警
                "check_interval": 60  # 60秒检查一次
            })
            
            # 自定义模板
            self.templates = self.config.get("templates", {
                "pre_market": "📊 **盘前市场概览**\n\n{market_summary}\n\n今日关注:\n{watchlist}\n\n$SPY 盘前: {spy_premarket}\n$QQQ 盘前: {qqq_premarket}",
                "market_open": "🔔 **市场开盘**\n\n{market_summary}\n\n关键指数:\n- $SPY: {spy_price} ({spy_change})\n- $QQQ: {qqq_price} ({qqq_change})\n\n今日焦点: {focus}",
                "mid_day": "📈 **午盘概览**\n\n{market_summary}\n\n表现最佳: {top_performers}\n表现最差: {worst_performers}\n\n特别关注: {special_focus}",
                "market_close": "🏁 **收盘总结**\n\n{market_summary}\n\n今日赢家: {winners}\n今日输家: {losers}\n\n明日展望: {tomorrow_outlook}",
                "after_hours": "🌙 **盘后更新**\n\n{market_summary}\n\n盘后异动: {after_hours_movers}\n\n重要财报: {earnings}",
                "evening": "📰 **晚间概览**\n\n{market_summary}\n\n明日关注: {tomorrow_watchlist}\n\n全球市场: {global_markets}",
                "whale_alert": "🐋 **大额交易预警**\n\n{symbol} 检测到大额交易!\n金额: ${amount:,.2f}M\n类型: {trade_type}\n\n{ai_analysis}",
                "volatility_alert": "⚠️ **异常波动预警**\n\n{symbol} 异常波动!\n变动: {change}%\n成交量: {volume:,}\n\n{ai_analysis}",
                "portfolio_update": "📊 **组合更新: {portfolio_name}**\n\n{ai_analysis}\n\n7日表现: {performance}\n\n风险等级: {risk_level}"
            })
            
            logger.info(f"社区调度器配置加载完成，时区: {self.timezone}")
        except Exception as e:
            logger.error(f"加载社区调度器配置失败: {e}")
            # 设置默认值
            self.enabled = True
            self.timezone = pytz.timezone("America/New_York")
            self.schedule_config = {
                "pre_market": {"enabled": True, "time": "09:00"},
                "market_open": {"enabled": True, "time": "09:30"},
                "mid_day": {"enabled": True, "time": "12:30"},
                "market_close": {"enabled": True, "time": "16:00"},
                "after_hours": {"enabled": True, "time": "16:30"},
                "evening": {"enabled": True, "time": "20:00"}
            }
            self.market_open_time = self._parse_time("09:30")
            self.market_close_time = self._parse_time("16:00")
            self.realtime_config = {
                "enabled": True,
                "whale_alert": True,
                "whale_threshold": 5000000,
                "volatility_alert": True,
                "volatility_threshold": 3.0,
                "check_interval": 60
            }
            self.templates = {}
    
    def _parse_time(self, time_str: str) -> datetime.time:
        """解析时间字符串为time对象"""
        try:
            hours, minutes = map(int, time_str.split(':'))
            return datetime.time(hours, minutes)
        except Exception as e:
            logger.error(f"解析时间字符串 {time_str} 失败: {e}")
            return datetime.time(0, 0)
    
    def _init_schedule(self):
        """初始化调度时间"""
        for task_name, task_config in self.schedule_config.items():
            if task_config.get("enabled", True):
                task_time = self._parse_time(task_config.get("time", "00:00"))
                self.next_execution[task_name] = self._get_next_execution_time(task_time)
                logger.info(f"计划任务 {task_name} 下次执行时间: {self.next_execution[task_name]}")
    
    def _get_next_execution_time(self, task_time: datetime.time) -> datetime.datetime:
        """获取任务下次执行时间"""
        now = datetime.datetime.now(self.timezone)
        next_time = datetime.datetime.combine(now.date(), task_time)
        next_time = self.timezone.localize(next_time)
        
        # 如果今天的时间已经过了，则安排到明天
        if next_time < now:
            next_time = next_time + datetime.timedelta(days=1)
            
        return next_time
    
    def _check_market_hours(self) -> bool:
        """检查当前是否为市场交易时间"""
        now = datetime.datetime.now(self.timezone)
        current_time = now.time()
        
        # 周末不是交易日
        if now.weekday() >= 5:  # 5=周六, 6=周日
            return False
            
        # 检查当前时间是否在交易时间内
        return self.market_open_time <= current_time < self.market_close_time
    
    def start(self):
        """启动调度器"""
        if not self.enabled:
            logger.info("社区调度器已禁用，不启动")
            return
            
        if self.running:
            logger.warning("社区调度器已在运行中")
            return
            
        self.running = True
        
        # 启动调度线程
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        # 启动事件处理线程
        self.event_thread = threading.Thread(target=self._event_loop, daemon=True)
        self.event_thread.start()
        
        logger.info("社区调度器已启动")
    
    def stop(self):
        """停止调度器"""
        if not self.running:
            logger.warning("社区调度器未在运行")
            return
            
        self.running = False
        
        # 等待线程结束
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=1.0)
            
        if self.event_thread and self.event_thread.is_alive():
            self.event_thread.join(timeout=1.0)
            
        logger.info("社区调度器已停止")
    
    def _scheduler_loop(self):
        """调度器主循环"""
        while self.running:
            try:
                # 检查是否为市场交易时间
                is_market_open = self._check_market_hours()
                if is_market_open != self.market_open:
                    self.market_open = is_market_open
                    logger.info(f"市场状态变更: {'开盘' if is_market_open else '休市'}")
                
                # 检查计划任务
                self._check_scheduled_tasks()
                
                # 如果市场开盘，检查实时监控任务
                if self.market_open and self.realtime_config.get("enabled", True):
                    self._add_realtime_check_event()
                
                # 睡眠一段时间
                time.sleep(10)  # 每10秒检查一次
            except Exception as e:
                logger.error(f"调度器循环出错: {e}")
                time.sleep(30)  # 出错后等待30秒再继续
    
    def _event_loop(self):
        """事件处理循环"""
        while self.running:
            try:
                # 从队列获取事件
                try:
                    event = self.event_queue.get(timeout=1.0)
                except:
                    continue
                    
                # 处理事件
                event_type = event.get("type")
                event_data = event.get("data", {})
                
                logger.info(f"处理事件: {event_type}")
                
                if event_type == "scheduled_task":
                    self._handle_scheduled_task(event_data)
                elif event_type == "realtime_check":
                    self._handle_realtime_check(event_data)
                elif event_type == "portfolio_update":
                    self._handle_portfolio_update(event_data)
                else:
                    logger.warning(f"未知事件类型: {event_type}")
                
                # 标记任务完成
                self.event_queue.task_done()
            except Exception as e:
                logger.error(f"事件处理循环出错: {e}")
                time.sleep(5)  # 出错后等待5秒再继续
    
    def _check_scheduled_tasks(self):
        """检查计划任务"""
        now = datetime.datetime.now(self.timezone)
        
        for task_name, next_time in list(self.next_execution.items()):
            if now >= next_time:
                # 添加到事件队列
                self.event_queue.put({
                    "type": "scheduled_task",
                    "data": {
                        "task_name": task_name,
                        "scheduled_time": next_time
                    }
                })
                
                # 更新下次执行时间
                task_time = self._parse_time(self.schedule_config[task_name].get("time", "00:00"))
                self.next_execution[task_name] = self._get_next_execution_time(task_time)
                self.last_execution[task_name] = now
                
                logger.info(f"计划任务 {task_name} 加入队列，下次执行时间: {self.next_execution[task_name]}")
    
    def _add_realtime_check_event(self):
        """添加实时监控事件"""
        # 检查上次检查时间，控制频率
        last_check = self.last_execution.get("realtime_check", datetime.datetime.min)
        now = datetime.datetime.now(self.timezone)
        check_interval = self.realtime_config.get("check_interval", 60)
        
        if (now - last_check).total_seconds() >= check_interval:
            self.event_queue.put({
                "type": "realtime_check",
                "data": {"timestamp": now}
            })
            self.last_execution["realtime_check"] = now
    
    def _handle_scheduled_task(self, event_data: Dict):
        """处理计划任务"""
        task_name = event_data.get("task_name")
        scheduled_time = event_data.get("scheduled_time")
        
        # 根据任务类型处理
        if task_name == "pre_market":
            self._handle_pre_market()
        elif task_name == "market_open":
            self._handle_market_open()
        elif task_name == "mid_day":
            self._handle_mid_day()
        elif task_name == "market_close":
            self._handle_market_close()
        elif task_name == "after_hours":
            self._handle_after_hours()
        elif task_name == "evening":
            self._handle_evening()
        else:
            logger.warning(f"未知任务类型: {task_name}")
            
        # 这里还可以添加所有组合的定期更新
        self._schedule_portfolio_updates()
    
    def _handle_realtime_check(self, event_data: Dict):
        """处理实时监控检查"""
        # 模拟实现：随机生成一些事件
        # 在实际实现中，这里应该从数据源获取实时数据并进行分析
        
        # 鲸鱼交易预警
        if self.realtime_config.get("whale_alert", True) and random.random() < 0.05:  # 5%概率触发
            self._generate_whale_alert()
        
        # 波动率预警
        if self.realtime_config.get("volatility_alert", True) and random.random() < 0.05:  # 5%概率触发
            self._generate_volatility_alert()
    
    def _handle_portfolio_update(self, event_data: Dict):
        """处理组合更新"""
        portfolio_id = event_data.get("portfolio_id")
        
        if not portfolio_id or portfolio_id not in self.portfolio_manager.portfolio.portfolios:
            logger.warning(f"尝试更新不存在的组合: {portfolio_id}")
            return
            
        try:
            # 获取组合信息
            portfolio = self.portfolio_manager.portfolio.portfolios[portfolio_id]
            portfolio_name = portfolio.get("name", "未命名组合")
            
            # 生成图表
            chart_path = self.portfolio_manager.generate_portfolio_chart(portfolio_id)
            
            # AI分析
            analysis = self.portfolio_manager.analyze_portfolio(portfolio_id)
            ai_analysis = analysis.get("analysis", "分析未能生成")
            
            # 获取性能数据
            perf_data = analysis.get("performance", {})
            total_return = perf_data.get("total_return", 0)
            sharpe = perf_data.get("sharpe", 0)
            
            # 计算风险等级
            risk_level = "中等"
            if sharpe > 1.5:
                risk_level = "低"
            elif sharpe < 0.5:
                risk_level = "高"
            
            # 格式化消息
            message = self.templates.get("portfolio_update", "📊 **组合更新: {portfolio_name}**\n\n{ai_analysis}\n\n7日表现: {performance}\n\n风险等级: {risk_level}")
            message = message.format(
                portfolio_name=portfolio_name,
                ai_analysis=ai_analysis,
                performance=f"{total_return:.2%}" if isinstance(total_return, (int, float)) else "未知",
                risk_level=risk_level
            )
            
            # 发送消息
            if self.notifier:
                self.notifier.send_message(message, image_path=chart_path)
                logger.info(f"发送组合更新: {portfolio_name}")
            else:
                logger.info(f"模拟发送组合更新: {message}")
        except Exception as e:
            logger.error(f"处理组合更新失败: {e}")
    
    def _schedule_portfolio_updates(self):
        """安排组合更新任务"""
        try:
            # 获取所有组合ID
            portfolio_ids = list(self.portfolio_manager.portfolio.portfolios.keys())
            
            # 随机选择一个组合进行更新
            if portfolio_ids:
                portfolio_id = random.choice(portfolio_ids)
                
                # 添加到事件队列
                self.event_queue.put({
                    "type": "portfolio_update",
                    "data": {"portfolio_id": portfolio_id}
                })
                
                logger.info(f"安排组合 {portfolio_id} 的更新")
        except Exception as e:
            logger.error(f"安排组合更新失败: {e}")
    
    def _generate_market_summary(self) -> str:
        """生成市场概览"""
        # 模拟实现，实际应该从市场数据获取
        market_conditions = ["震荡", "上涨", "下跌", "高波动", "横盘整理"]
        condition = random.choice(market_conditions)
        
        prompts = [
            f"请简要分析当前{condition}市场环境下的主要趋势，宏观因素和投资机会（50字以内）",
            f"以专业量化分析师的身份，总结当前{condition}行情的关键特点和预期方向（50字以内）",
            f"请针对今日{condition}市场，提供一个简短的市场分析和交易建议（50字以内）"
        ]
        
        prompt = random.choice(prompts)
        
        try:
            # 调用AI生成
            market_summary = self.ai_router.ask(prompt)
            return market_summary
        except Exception as e:
            logger.error(f"生成市场概览失败: {e}")
            return f"市场目前呈{condition}趋势，需谨慎操作。"
    
    def _handle_pre_market(self):
        """处理盘前任务"""
        market_summary = self._generate_market_summary()
        
        # 模拟数据
        spy_premarket = f"{random.uniform(-1.0, 1.0):.2f}%"
        qqq_premarket = f"{random.uniform(-1.0, 1.0):.2f}%"
        watchlist = "AAPL, MSFT, GOOGL, AMZN, NVDA"
        
        # 格式化消息
        message = self.templates.get("pre_market", "📊 **盘前市场概览**\n\n{market_summary}\n\n今日关注:\n{watchlist}\n\n$SPY 盘前: {spy_premarket}\n$QQQ 盘前: {qqq_premarket}")
        message = message.format(
            market_summary=market_summary,
            watchlist=watchlist,
            spy_premarket=spy_premarket,
            qqq_premarket=qqq_premarket
        )
        
        # 发送消息
        if self.notifier:
            self.notifier.send_message(message)
            logger.info("发送盘前消息")
        else:
            logger.info(f"模拟发送盘前消息: {message}")
    
    def _handle_market_open(self):
        """处理开盘任务"""
        market_summary = self._generate_market_summary()
        
        # 模拟数据
        spy_price = round(random.uniform(400, 440), 2)
        spy_change = f"{random.uniform(-1.0, 1.0):.2f}%"
        qqq_price = round(random.uniform(350, 390), 2)
        qqq_change = f"{random.uniform(-1.0, 1.0):.2f}%"
        
        # 生成今日焦点
        focus_prompt = "请作为量化分析师，提供今日市场焦点和需要关注的重要事件（50字以内）"
        try:
            focus = self.ai_router.ask(focus_prompt)
        except:
            focus = "今日关注美联储官员讲话和科技股财报情况"
        
        # 格式化消息
        message = self.templates.get("market_open", "🔔 **市场开盘**\n\n{market_summary}\n\n关键指数:\n- $SPY: {spy_price} ({spy_change})\n- $QQQ: {qqq_price} ({qqq_change})\n\n今日焦点: {focus}")
        message = message.format(
            market_summary=market_summary,
            spy_price=spy_price,
            spy_change=spy_change,
            qqq_price=qqq_price,
            qqq_change=qqq_change,
            focus=focus
        )
        
        # 发送消息
        if self.notifier:
            self.notifier.send_message(message)
            logger.info("发送开盘消息")
        else:
            logger.info(f"模拟发送开盘消息: {message}")
    
    def _handle_mid_day(self):
        """处理午盘任务"""
        market_summary = self._generate_market_summary()
        
        # 模拟数据
        top_performers = "AAPL (+2.3%), NVDA (+1.8%), MSFT (+1.5%)"
        worst_performers = "AMD (-1.7%), TSLA (-1.3%), AMZN (-0.9%)"
        
        # 生成特别关注
        special_focus_prompt = "请作为资深交易员，分析目前市场主要板块轮动和资金流向情况（50字以内）"
        try:
            special_focus = self.ai_router.ask(special_focus_prompt)
        except:
            special_focus = "资金主要流入科技和医疗板块，周期股明显走弱"
        
        # 格式化消息
        message = self.templates.get("mid_day", "📈 **午盘概览**\n\n{market_summary}\n\n表现最佳: {top_performers}\n表现最差: {worst_performers}\n\n特别关注: {special_focus}")
        message = message.format(
            market_summary=market_summary,
            top_performers=top_performers,
            worst_performers=worst_performers,
            special_focus=special_focus
        )
        
        # 发送消息
        if self.notifier:
            self.notifier.send_message(message)
            logger.info("发送午盘消息")
        else:
            logger.info(f"模拟发送午盘消息: {message}")
    
    def _handle_market_close(self):
        """处理收盘任务"""
        market_summary = self._generate_market_summary()
        
        # 模拟数据
        winners = "科技 (+1.2%), 医疗 (+0.8%), 能源 (+0.5%)"
        losers = "公用事业 (-0.7%), 房地产 (-0.6%), 消费 (-0.4%)"
        
        # 生成明日展望
        outlook_prompt = "请作为资深分析师，预测明日市场可能的走势和关注要点（50字以内）"
        try:
            tomorrow_outlook = self.ai_router.ask(outlook_prompt)
        except:
            tomorrow_outlook = "明日关注CPI数据发布，或将引发市场波动"
        
        # 格式化消息
        message = self.templates.get("market_close", "🏁 **收盘总结**\n\n{market_summary}\n\n今日赢家: {winners}\n今日输家: {losers}\n\n明日展望: {tomorrow_outlook}")
        message = message.format(
            market_summary=market_summary,
            winners=winners,
            losers=losers,
            tomorrow_outlook=tomorrow_outlook
        )
        
        # 发送消息
        if self.notifier:
            self.notifier.send_message(message)
            logger.info("发送收盘消息")
        else:
            logger.info(f"模拟发送收盘消息: {message}")
    
    def _handle_after_hours(self):
        """处理盘后任务"""
        market_summary = self._generate_market_summary()
        
        # 模拟数据
        after_hours_movers = "AAPL (+0.8% 财报超预期), TSLA (-1.2% CEO言论影响)"
        earnings = "明日财报: AMZN, MSFT, META"
        
        # 格式化消息
        message = self.templates.get("after_hours", "🌙 **盘后更新**\n\n{market_summary}\n\n盘后异动: {after_hours_movers}\n\n重要财报: {earnings}")
        message = message.format(
            market_summary=market_summary,
            after_hours_movers=after_hours_movers,
            earnings=earnings
        )
        
        # 发送消息
        if self.notifier:
            self.notifier.send_message(message)
            logger.info("发送盘后消息")
        else:
            logger.info(f"模拟发送盘后消息: {message}")
    
    def _handle_evening(self):
        """处理晚间任务"""
        market_summary = self._generate_market_summary()
        
        # 模拟数据
        tomorrow_watchlist = "AMZN (财报), JJ (新药获批), BA (交付更新)"
        global_markets = "亚洲: 涨跌互现, 欧洲: 普遍上涨, 加密: BTC +2.1%"
        
        # 格式化消息
        message = self.templates.get("evening", "📰 **晚间概览**\n\n{market_summary}\n\n明日关注: {tomorrow_watchlist}\n\n全球市场: {global_markets}")
        message = message.format(
            market_summary=market_summary,
            tomorrow_watchlist=tomorrow_watchlist,
            global_markets=global_markets
        )
        
        # 发送消息
        if self.notifier:
            self.notifier.send_message(message)
            logger.info("发送晚间消息")
        else:
            logger.info(f"模拟发送晚间消息: {message}")
    
    def _generate_whale_alert(self):
        """生成鲸鱼交易预警"""
        # 模拟数据
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "AMD", "META"]
        symbol = random.choice(symbols)
        amount = random.uniform(5, 50)  # 百万美元
        trade_type = random.choice(["买入", "卖出", "期权买入", "期权卖出"])
        
        # 生成AI分析
        analysis_prompt = f"请作为量化交易分析师，对{symbol}股票的大额{trade_type}交易进行简短分析，可能的影响和后续走势（50字以内）"
        try:
            ai_analysis = self.ai_router.ask(analysis_prompt)
        except:
            ai_analysis = f"这笔{trade_type}可能预示着机构对{symbol}的看法发生变化，后续价格或有明显波动"
        
        # 格式化消息
        message = self.templates.get("whale_alert", "🐋 **大额交易预警**\n\n{symbol} 检测到大额交易!\n金额: ${amount:,.2f}M\n类型: {trade_type}\n\n{ai_analysis}")
        message = message.format(
            symbol=symbol,
            amount=amount,
            trade_type=trade_type,
            ai_analysis=ai_analysis
        )
        
        # 发送消息
        if self.notifier:
            self.notifier.send_message(message)
            logger.info(f"发送鲸鱼预警: {symbol}")
        else:
            logger.info(f"模拟发送鲸鱼预警: {message}")
    
    def _generate_volatility_alert(self):
        """生成波动率预警"""
        # 模拟数据
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "AMD", "META"]
        symbol = random.choice(symbols)
        change = random.uniform(3.0, 10.0) * random.choice([1, -1])  # 正负波动
        volume = random.randint(1000000, 10000000)  # 成交量
        
        # 生成AI分析
        direction = "上涨" if change > 0 else "下跌"
        analysis_prompt = f"请分析{symbol}股票突然{direction}{abs(change):.2f}%的可能原因和后续走势（50字以内）"
        try:
            ai_analysis = self.ai_router.ask(analysis_prompt)
        except:
            ai_analysis = f"{symbol}的急剧{direction}可能与市场消息流动有关，建议观察成交量变化确认趋势"
        
        # 格式化消息
        message = self.templates.get("volatility_alert", "⚠️ **异常波动预警**\n\n{symbol} 异常波动!\n变动: {change}%\n成交量: {volume:,}\n\n{ai_analysis}")
        message = message.format(
            symbol=symbol,
            change=f"{change:.2f}",
            volume=volume,
            ai_analysis=ai_analysis
        )
        
        # 发送消息
        if self.notifier:
            self.notifier.send_message(message)
            logger.info(f"发送波动预警: {symbol}")
        else:
            logger.info(f"模拟发送波动预警: {message}")
    
    def send_custom_alert(self, alert_type: str, data: Dict):
        """
        发送自定义预警
        
        Args:
            alert_type: 预警类型
            data: 预警数据
        """
        if not self.running:
            logger.warning("社区调度器未运行，忽略自定义预警")
            return
        
        # 添加到事件队列
        self.event_queue.put({
            "type": alert_type,
            "data": data
        })
        logger.info(f"添加自定义预警: {alert_type}")

# 示例用法
def main():
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 模拟通知器
    class MockNotifier:
        def send_message(self, message, image_path=None):
            print(f"\n==== MOCK NOTIFICATION ====")
            print(f"Message: {message}")
            if image_path:
                print(f"Image: {image_path}")
            print("============================\n")
    
    notifier = MockNotifier()
    
    # 创建并启动调度器
    scheduler = CommunityScheduler(notifier=notifier)
    scheduler.start()
    
    try:
        # 运行一段时间用于测试
        print("调度器已启动，等待任务执行...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n接收到中断，停止调度器...")
        scheduler.stop()
        print("调度器已停止")

if __name__ == "__main__":
    main() 