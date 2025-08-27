"""
AI交易员工作流管理器
集成语音摘要、图表报告和市场事件监控等多个模块
实现全天候AI交易助理工作流
"""

import os
import json
import logging
import time
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta
from pathlib import Path
import threading
import asyncio
import pandas as pd
import numpy as np

# 导入自定义模块
from utils.ai_voice_summarizer import voice_summarizer
from utils.ai_chart_reporter import chart_reporter
from api.market_event_watcher import event_watcher
from utils.deepseek_api import get_deepseek_response

logger = logging.getLogger(__name__)

class AITraderWorkflow:
    """AI交易员工作流管理器"""
    
    def __init__(self):
        """初始化AI交易员工作流管理器"""
        self.telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        self.deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
        
        # 加载组件
        self.voice_summarizer = voice_summarizer
        self.chart_reporter = chart_reporter
        self.event_watcher = event_watcher
        
        # 工作流定时任务
        self.scheduled_tasks = {}
        self.stop_flag = False
        
        # 交易模式配置
        self.trading_mode = "daytrade"  # 'daytrade', 'swing', 'options'
        
        # 市场时间设置 (美东时间，需根据当前时区调整)
        self.market_hours = {
            "pre_market_start": "07:00",
            "market_open": "09:30",
            "midday_check": "12:00",
            "market_close": "16:00",
            "post_market_end": "20:00",
            "overnight_check": "22:00"
        }
        
        # 每日工作流程序
        self.workflow_sequence = [
            "pre_market_preparation",
            "market_open_briefing",
            "midday_checkpoint",
            "market_close_summary",
            "overnight_risk_assessment"
        ]
        
        # 当日交易数据
        self.trading_data = {
            "trades": [],
            "strategies": {},
            "pnl_series": [],
            "market_events": [],
            "active_positions": {}
        }
        
        logger.info("AI交易员工作流管理器初始化完成")
    
    #---------------------------#
    # 工作流定时任务调度 #
    #---------------------------#
    
    def start_workflow(self, webhook_port: int = 8000):
        """
        启动AI交易员工作流
        
        Args:
            webhook_port: Webhook服务器端口
        """
        logger.info("启动AI交易员工作流...")
        
        # 启动市场事件监听器
        self._start_event_watcher(webhook_port)
        
        # 计算今日工作流时间点
        self._schedule_today_workflow()
        
        # 启动工作流调度线程
        self.stop_flag = False
        scheduler_thread = threading.Thread(target=self._workflow_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        logger.info("AI交易员工作流已启动")
        
        # 发送启动通知
        self._send_startup_notification()
    
    def stop_workflow(self):
        """停止AI交易员工作流"""
        logger.info("正在停止AI交易员工作流...")
        self.stop_flag = True
        logger.info("AI交易员工作流已停止")
    
    def _start_event_watcher(self, port: int = 8000):
        """启动市场事件监听器"""
        try:
            # 使用独立线程启动Webhook服务器
            self.event_watcher.start_server_thread(port=port)
            logger.info(f"市场事件监听器已在端口 {port} 启动")
        except Exception as e:
            logger.error(f"启动市场事件监听器失败: {str(e)}")
    
    def _schedule_today_workflow(self):
        """计算并安排今日工作流时间点"""
        now = datetime.now()
        today = now.date()
        
        # 清空之前的任务
        self.scheduled_tasks = {}
        
        # 计算今日各时间点
        for task_name, time_str in self.market_hours.items():
            hour, minute = map(int, time_str.split(':'))
            task_time = datetime.combine(today, datetime.min.time()) + timedelta(hours=hour, minutes=minute)
            
            # 如果时间已过，则跳过（除非是收盘后总结）
            if task_time < now and task_name not in ["market_close_summary", "overnight_risk_assessment"]:
                continue
            
            # 将任务添加到计划
            self.scheduled_tasks[task_name] = {
                "scheduled_time": task_time,
                "executed": False,
                "workflow_function": getattr(self, f"_{task_name}_workflow", None)
            }
        
        logger.info(f"今日工作流已安排，共 {len(self.scheduled_tasks)} 个任务")
    
    def _workflow_scheduler(self):
        """工作流调度器主循环"""
        logger.info("工作流调度器已启动")
        
        while not self.stop_flag:
            now = datetime.now()
            
            # 检查是否有需要执行的任务
            for task_name, task_info in self.scheduled_tasks.items():
                if not task_info["executed"] and now >= task_info["scheduled_time"]:
                    logger.info(f"执行计划任务: {task_name}")
                    
                    # 执行任务
                    if task_info["workflow_function"]:
                        try:
                            task_info["workflow_function"]()
                            task_info["executed"] = True
                            logger.info(f"任务 {task_name} 执行完成")
                        except Exception as e:
                            logger.error(f"执行任务 {task_name} 时出错: {str(e)}")
                    else:
                        logger.warning(f"任务 {task_name} 没有对应的工作流函数")
            
            # 检查是否所有任务都已执行
            all_executed = all(task["executed"] for task in self.scheduled_tasks.values())
            
            # 如果当前是新的一天且所有任务都已执行，则重新安排任务
            if all_executed and now.hour >= 0 and now.hour < 1:
                self._schedule_today_workflow()
                logger.info("已重新安排明日工作流任务")
            
            # 休眠一段时间
            time.sleep(30)
    
    #---------------------------#
    # 工作流程序实现 #
    #---------------------------#
    
    def _pre_market_preparation_workflow(self):
        """
        盘前准备工作流
        - 市场数据扫描
        - AI判断市场模式
        - 策略自动打标签
        """
        logger.info("执行盘前准备工作流")
        
        # 1. 获取市场数据
        market_data = self._get_market_data_summary()
        
        # 2. 生成AI盘前分析
        pre_market_analysis = self._generate_ai_pre_market_analysis(market_data)
        
        # 3. 生成今日策略建议
        strategy_suggestions = self._generate_strategy_suggestions(pre_market_analysis)
        
        # 4. 组合消息
        message = f"""
📊 [AI盘前共识 & 策略准备]

市场模式预判：{pre_market_analysis.get('market_mode', '未知')}
预期波动率：{pre_market_analysis.get('expected_volatility', '未知')} (VIX {pre_market_analysis.get('vix', '未知')})
重大事件：{pre_market_analysis.get('major_events', '无')}

今日拟启用策略：
"""
        
        # 添加策略列表
        for strategy in strategy_suggestions:
            message += f"✅ {strategy}\n"
        
        message += f"\n🔧 系统状态正常 | 全策略准备就绪"
        
        # 5. 发送消息到Telegram
        self._send_to_telegram(message)
        
        # 6. 生成并发送语音摘要
        self._send_voice_summary(message, "market_open")
        
        logger.info("盘前准备工作流执行完成")
    
    def _market_open_briefing_workflow(self):
        """
        盘中开盘简报工作流
        - 开盘状态通知
        - 初步策略激活
        """
        logger.info("执行开盘简报工作流")
        
        # 1. 获取开盘状态
        market_open_data = self._get_market_open_data()
        
        # 2. 组合消息
        message = f"""
🔔 [市场开盘 & 初始策略部署]

市场开盘状态：{market_open_data.get('market_status', '正常')}
主要指数：
- S&P 500: {market_open_data.get('spy_price', 'N/A')} ({market_open_data.get('spy_change', 'N/A')})
- QQQ: {market_open_data.get('qqq_price', 'N/A')} ({market_open_data.get('qqq_change', 'N/A')})
- VIX: {market_open_data.get('vix', 'N/A')}

已激活策略：
"""
        
        # 添加激活的策略
        for strategy, status in market_open_data.get('active_strategies', {}).items():
            message += f"✅ {strategy} - {status}\n"
        
        message += f"\n📱 交易系统已连接 | 监控中"
        
        # 3. 发送消息到Telegram
        self._send_to_telegram(message)
        
        logger.info("开盘简报工作流执行完成")
    
    def _midday_checkpoint_workflow(self):
        """
        午盘检查点工作流
        - 上午表现总结
        - AI调整策略
        """
        logger.info("执行午盘检查点工作流")
        
        # 1. 获取上午交易数据
        midday_data = self._get_midday_trading_data()
        
        # 2. 组合消息
        message = f"""
🕛 [午盘AI市场复盘]

当前总P&L: ${midday_data.get('current_pnl', 0):.2f}
上午市场模式：{midday_data.get('morning_market_mode', '未知')}
AI判定：{midday_data.get('ai_assessment', '未知')}

下午继续执行：
"""
        
        # 添加下午继续的策略
        active_strategies = midday_data.get('active_strategies', [])
        paused_strategies = midday_data.get('paused_strategies', [])
        
        for strategy in active_strategies:
            message += f"✅ {strategy}\n"
        
        for strategy in paused_strategies:
            message += f"❌ 暂停 {strategy}\n"
        
        # 3. 发送消息到Telegram
        self._send_to_telegram(message)
        
        # 4. 生成并发送上午PnL图表
        if 'pnl_data' in midday_data:
            self._send_pnl_chart(midday_data['pnl_data'], "上午交易盈亏曲线")
        
        # 5. 生成并发送语音摘要
        self._send_voice_summary(message, "midday")
        
        logger.info("午盘检查点工作流执行完成")
    
    def _market_close_summary_workflow(self):
        """
        收盘总结工作流
        - 今日交易总结
        - 策略表现分析
        - AI学习反馈
        """
        logger.info("执行收盘总结工作流")
        
        # 1. 获取全日交易数据
        daily_data = self._get_daily_trading_data()
        
        # 2. 组合消息
        message = f"""
📌 [盘后总结 & AI策略反馈]

今日盈亏: ${daily_data.get('total_pnl', 0):.2f}
活跃策略: {len(daily_data.get('strategies', {}))}个
胜率最高: {daily_data.get('best_strategy', '无')} (${daily_data.get('best_strategy_pnl', 0):.2f})
表现较差: {daily_data.get('worst_strategy', '无')} (${daily_data.get('worst_strategy_pnl', 0):.2f})

AI反馈：
- {daily_data.get('ai_feedback', ['无'])[0]}
- {daily_data.get('ai_feedback', ['', '无'])[1]}

✅ AI已生成优化方案，待复盘确认
"""
        
        # 3. 发送消息到Telegram
        self._send_to_telegram(message)
        
        # 4. 生成并发送全日PnL图表
        if 'pnl_data' in daily_data:
            self._send_pnl_chart(daily_data['pnl_data'], "今日交易盈亏曲线")
        
        # 5. 生成并发送策略分布图
        if 'strategy_results' in daily_data:
            self._send_strategy_chart(daily_data['strategy_results'], "今日策略绩效分布")
        
        # 6. 生成并发送语音摘要
        self._send_voice_summary(message, "market_close")
        
        logger.info("收盘总结工作流执行完成")
    
    def _overnight_risk_assessment_workflow(self):
        """
        夜盘风险评估工作流
        - 全球市场扫描
        - 次日AI初步预判
        """
        logger.info("执行夜盘风险评估工作流")
        
        # 1. 获取全球市场数据
        global_data = self._get_global_market_data()
        
        # 2. 生成AI次日预判
        next_day_forecast = self._generate_ai_next_day_forecast(global_data)
        
        # 3. 组合消息
        message = f"""
🌙 [夜盘全球扫描 & 明日准备]

全球风险概览：
- 美股期指: {global_data.get('us_futures', '未知')}
- VIX: {global_data.get('vix_status', '未知')}
- {global_data.get('major_events', '无重大事件预期')}

AI初步建议：
"""
        
        # 添加AI建议
        for suggestion in next_day_forecast.get('strategy_suggestions', []):
            message += f"✅ {suggestion}\n"
        
        message += f"\nAI已生成明日预案，明晨6:00自动更新"
        
        # 4. 发送消息到Telegram
        self._send_to_telegram(message)
        
        logger.info("夜盘风险评估工作流执行完成")
    
    #---------------------------#
    # 工具函数 #
    #---------------------------#
    
    def _send_to_telegram(self, message: str) -> bool:
        """
        发送消息到Telegram
        
        Args:
            message: 要发送的消息
            
        Returns:
            是否发送成功
        """
        try:
            import telegram
            
            if not self.telegram_token or not self.telegram_chat_id:
                logger.warning("未设置Telegram配置，消息发送失败")
                return False
            
            bot = telegram.Bot(token=self.telegram_token)
            bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode="Markdown"
            )
            
            logger.info("成功发送消息到Telegram")
            return True
        except Exception as e:
            logger.error(f"发送消息到Telegram时出错: {str(e)}")
            return False
    
    def _send_voice_summary(self, text: str, summary_type: str = "trading_day") -> bool:
        """
        生成并发送语音摘要
        
        Args:
            text: 原始文本
            summary_type: 摘要类型
            
        Returns:
            是否发送成功
        """
        try:
            result = self.voice_summarizer.generate_and_send_voice_summary(
                text, 
                summary_type=summary_type
            )
            return result.get("success", False)
        except Exception as e:
            logger.error(f"发送语音摘要时出错: {str(e)}")
            return False
    
    def _send_pnl_chart(self, pnl_data: Union[pd.Series, List[float]], title: str) -> bool:
        """
        生成并发送盈亏图表
        
        Args:
            pnl_data: 盈亏数据
            title: 图表标题
            
        Returns:
            是否发送成功
        """
        try:
            result = self.chart_reporter.generate_and_send_pnl_chart(
                pnl_data,
                title=title
            )
            return result.get("telegram_sent", False)
        except Exception as e:
            logger.error(f"发送盈亏图表时出错: {str(e)}")
            return False
    
    def _send_strategy_chart(self, strategy_results: Dict[str, float], title: str) -> bool:
        """
        生成并发送策略分布图
        
        Args:
            strategy_results: 策略结果字典
            title: 图表标题
            
        Returns:
            是否发送成功
        """
        try:
            result = self.chart_reporter.generate_and_send_strategy_chart(
                strategy_results,
                title=title
            )
            return result.get("telegram_sent", False)
        except Exception as e:
            logger.error(f"发送策略分布图时出错: {str(e)}")
            return False
    
    def _send_startup_notification(self):
        """发送启动通知"""
        message = f"""
🚀 *AI交易助手系统已启动*

模式: {self.trading_mode.upper()}
当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
今日工作流: {len(self.scheduled_tasks)} 个任务已排程

✅ 系统状态: 正常运行
"""
        self._send_to_telegram(message)
    
    #---------------------------#
    # 数据获取函数（示例实现，需根据实际数据源调整） #
    #---------------------------#
    
    def _get_market_data_summary(self) -> Dict[str, Any]:
        """获取市场数据摘要（示例）"""
        # 在实际实现中，这里应该连接到真实的市场数据源
        return {
            "vix": "14.3",
            "spy_futures": "+0.2%",
            "major_events": "无",
            "market_sentiment": "中性",
            "volume_prediction": "正常",
            "premarket_gainers": ["AAPL", "MSFT", "NVDA"],
            "premarket_losers": ["META", "AMD", "TSLA"]
        }
    
    def _generate_ai_pre_market_analysis(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成AI盘前分析（示例）"""
        # 在实际实现中，这里应该调用DeepSeek API
        return {
            "market_mode": "震荡",
            "expected_volatility": "中等",
            "vix": "14.3",
            "major_events": "无",
            "prediction": "今日市场预计震荡为主，无明显趋势"
        }
    
    def _generate_strategy_suggestions(self, analysis: Dict[str, Any]) -> List[str]:
        """生成策略建议（示例）"""
        # 根据市场模式选择适合的策略
        market_mode = analysis.get("market_mode", "未知")
        
        if market_mode == "震荡":
            return [
                "Options Gamma Scalping",
                "Mean Reversion (5min Bar)",
                "AI Smart Flow Tracker (机构大单跟踪)"
            ]
        elif market_mode == "趋势":
            return [
                "Breakout Momentum",
                "Options Trend Rider",
                "Moving Average Crossover"
            ]
        elif market_mode == "高波动":
            return [
                "Volatility Arbitrage",
                "Straddle Strategy",
                "Adaptive RSI"
            ]
        else:
            return [
                "Dynamic Beta Strategy",
                "Balanced Allocation",
                "Risk Parity"
            ]
    
    def _get_market_open_data(self) -> Dict[str, Any]:
        """获取开盘数据（示例）"""
        return {
            "market_status": "正常",
            "spy_price": "427.80",
            "spy_change": "+0.3%",
            "qqq_price": "363.50",
            "qqq_change": "+0.5%",
            "vix": "14.2",
            "active_strategies": {
                "Options Gamma Scalping": "就绪",
                "Mean Reversion (5min Bar)": "监控中",
                "AI Smart Flow Tracker": "扫描中"
            }
        }
    
    def _get_midday_trading_data(self) -> Dict[str, Any]:
        """获取午盘交易数据（示例）"""
        # 生成模拟盈亏数据
        pnl_data = pd.Series([100, -50, 200, 150, -120, 300, 250, -80, 100, 200])
        
        return {
            "current_pnl": 620,
            "morning_market_mode": "震荡反复，趋势信号多失败",
            "ai_assessment": "下午趋势概率较低，主推震荡策略",
            "active_strategies": ["Mean Reversion", "Options Gamma Scalping"],
            "paused_strategies": ["Breakout Strategy"],
            "pnl_data": pnl_data
        }
    
    def _get_daily_trading_data(self) -> Dict[str, Any]:
        """获取全日交易数据（示例）"""
        # 生成模拟盈亏数据
        pnl_data = pd.Series([100, -50, 200, 150, -120, 300, 250, -80, 100, 200, 150, -90, 180, 220])
        
        # 生成模拟策略结果
        strategy_results = {
            "Mean Reversion": 340.0,
            "Gamma Scalping": 520.0,
            "Breakout V2": -120.0,
            "RSI Strategy": 250.0,
            "Options Flow": -80.0
        }
        
        return {
            "total_pnl": 1200,
            "trade_count": 25,
            "win_rate": 0.68,
            "best_strategy": "Gamma Scalping",
            "best_strategy_pnl": 520.0,
            "worst_strategy": "Breakout V2",
            "worst_strategy_pnl": -120.0,
            "strategies": strategy_results,
            "pnl_data": pnl_data,
            "strategy_results": strategy_results,
            "ai_feedback": [
                "Breakout V2进入优化队列",
                "明日建议继续主打震荡策略"
            ]
        }
    
    def _get_global_market_data(self) -> Dict[str, Any]:
        """获取全球市场数据（示例）"""
        return {
            "us_futures": "偏多",
            "vix_status": "低位",
            "asia_markets": "涨跌互现",
            "europe_markets": "小幅上涨",
            "forex": "美元走强",
            "commodities": "原油小幅上涨",
            "major_events": "无重大事件预期"
        }
    
    def _generate_ai_next_day_forecast(self, global_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成AI次日预判（示例）"""
        return {
            "market_trend": "偏多震荡",
            "expected_volatility": "低",
            "strategy_suggestions": [
                "保持震荡策略组合",
                "纳入AI趋势追踪作为备选"
            ],
            "sectors_to_watch": ["科技", "医疗", "半导体"],
            "risk_assessment": "低风险"
        }

# 单例模式，方便直接导入
trader_workflow = AITraderWorkflow()

# 测试代码
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 启动AI交易员工作流...")
    
    # 创建并启动工作流
    workflow = AITraderWorkflow()
    
    # 启动服务器和工作流
    workflow.start_workflow(webhook_port=8000)
    
    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("正在停止服务...")
        workflow.stop_workflow()
        print("服务已停止") 