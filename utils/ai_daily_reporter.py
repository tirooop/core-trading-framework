"""
AI交易日报生成器
生成每日交易报告，包括盈亏图表、策略分布和语音摘要
支持定时自动生成和按需生成
"""

import os
import logging
from typing import Optional, Dict, Any, List, Union, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
from pathlib import Path

# 导入自定义模块
from utils.ai_chart_reporter import chart_reporter
from utils.ai_voice_summarizer import voice_summarizer
from utils.notifier_dispatcher import notifier
from utils.deepseek_api import get_deepseek_response

logger = logging.getLogger(__name__)

class AIDailyReporter:
    """AI交易日报生成器"""
    
    def __init__(self):
        """初始化AI交易日报生成器"""
        self.deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
        
        # 报告历史记录
        self.report_history = []
        self.max_history_size = 30  # 保存最近30天的报告
        
        # 报告存储目录
        self.reports_dir = Path("trade_reports")
        self.reports_dir.mkdir(exist_ok=True)
        
        logger.info("AI交易日报生成器初始化完成")
    
    def generate_daily_report(self, 
                            strategies_data: List[Dict[str, Any]], 
                            market_data: Optional[Dict[str, Any]] = None,
                            report_type: str = "daily",
                            send_notification: bool = True) -> Dict[str, Any]:
        """
        生成每日交易报告
        
        Args:
            strategies_data: 策略数据列表
            market_data: 市场数据，可选
            report_type: 报告类型（daily, weekly, monthly）
            send_notification: 是否发送通知
            
        Returns:
            报告结果字典
        """
        logger.info(f"正在生成{report_type}交易报告...")
        
        # 创建结果字典
        result = {
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "report_type": report_type,
            "charts": [],
            "summary": "",
            "strategies_count": len(strategies_data)
        }
        
        try:
            # 转换策略数据为Pandas DataFrame
            df = pd.DataFrame(strategies_data)
            
            # 计算总体统计信息
            total_pnl = df['pnl'].sum() if 'pnl' in df.columns else 0
            avg_win_rate = df['win_rate'].mean() if 'win_rate' in df.columns else 0
            total_trades = df['trades'].sum() if 'trades' in df.columns else 0
            
            # 找出表现最好和最差的策略
            if 'pnl' in df.columns and not df.empty:
                best_strategy = df.loc[df['pnl'].idxmax()]
                worst_strategy = df.loc[df['pnl'].idxmin()]
                best_strategy_name = best_strategy.get('name', 'Unknown')
                worst_strategy_name = worst_strategy.get('name', 'Unknown')
                best_strategy_pnl = best_strategy.get('pnl', 0)
                worst_strategy_pnl = worst_strategy.get('pnl', 0)
            else:
                best_strategy_name = worst_strategy_name = "未知"
                best_strategy_pnl = worst_strategy_pnl = 0
            
            # 保存统计信息到结果
            result.update({
                "total_pnl": total_pnl,
                "avg_win_rate": avg_win_rate,
                "total_trades": total_trades,
                "best_strategy": best_strategy_name,
                "worst_strategy": worst_strategy_name,
                "best_strategy_pnl": best_strategy_pnl,
                "worst_strategy_pnl": worst_strategy_pnl
            })
            
            # 1. 生成盈亏图表
            if 'pnl_series' in df.columns:
                # 如果有时间序列PnL数据
                pnl_series = pd.concat([pd.Series(row['pnl_series']) for _, row in df.iterrows()], axis=1).sum(axis=1)
                chart_path = self._generate_pnl_chart(pnl_series, f"{report_type.capitalize()}交易盈亏曲线")
                if chart_path:
                    result["charts"].append({"type": "pnl", "path": chart_path})
            
            # 2. 生成策略分布图
            strategy_results = {}
            if 'name' in df.columns and 'pnl' in df.columns:
                for _, row in df.iterrows():
                    strategy_results[row['name']] = row['pnl']
                
                chart_path = self._generate_strategy_distribution(strategy_results, f"{report_type.capitalize()}策略绩效分布")
                if chart_path:
                    result["charts"].append({"type": "distribution", "path": chart_path})
            
            # 3. 生成AI总结
            summary = self._generate_ai_summary(df, market_data, report_type)
            result["summary"] = summary
            
            # 4. 保存报告到文件
            report_path = self._save_report_to_file(result, report_type)
            result["report_path"] = report_path
            
            # 5. 发送通知（如果需要）
            if send_notification:
                self._send_report_notification(result, report_type)
            
            # 更新历史记录
            self._add_to_history(result)
            
            result["success"] = True
            logger.info(f"{report_type.capitalize()}交易报告生成成功")
            
            return result
        
        except Exception as e:
            error_msg = f"生成交易报告时出错: {str(e)}"
            logger.error(error_msg)
            result["error"] = error_msg
            return result
    
    def _generate_pnl_chart(self, pnl_data: Union[pd.Series, List[float]], title: str) -> Optional[str]:
        """
        生成盈亏图表
        
        Args:
            pnl_data: 盈亏数据
            title: 图表标题
            
        Returns:
            图表路径，如果生成失败则返回None
        """
        try:
            result = chart_reporter.generate_pnl_chart(pnl_data, title)
            return result.get("chart_path") if result.get("success", False) else None
        except Exception as e:
            logger.error(f"生成盈亏图表时出错: {str(e)}")
            return None
    
    def _generate_strategy_distribution(self, strategy_results: Dict[str, float], title: str) -> Optional[str]:
        """
        生成策略分布图
        
        Args:
            strategy_results: 策略结果字典
            title: 图表标题
            
        Returns:
            图表路径，如果生成失败则返回None
        """
        try:
            result = chart_reporter.generate_strategy_distribution_chart(strategy_results, title)
            return result.get("chart_path") if result.get("success", False) else None
        except Exception as e:
            logger.error(f"生成策略分布图时出错: {str(e)}")
            return None
    
    def _generate_ai_summary(self, 
                           df: pd.DataFrame, 
                           market_data: Optional[Dict[str, Any]], 
                           report_type: str) -> str:
        """
        生成AI摘要
        
        Args:
            df: 策略数据DataFrame
            market_data: 市场数据
            report_type: 报告类型
            
        Returns:
            AI生成的摘要文本
        """
        try:
            # 提取关键数据
            total_pnl = df['pnl'].sum() if 'pnl' in df.columns else 0
            avg_win_rate = df['win_rate'].mean() if 'win_rate' in df.columns else 0
            total_trades = df['trades'].sum() if 'trades' in df.columns else 0
            
            # 准备提示
            if report_type == "daily":
                system_prompt = "你是一位专业量化交易员的AI助手，负责分析每日交易表现并提供简短精确的总结。使用客观、专业的语言，突出关键数据和洞察。"
            elif report_type == "weekly":
                system_prompt = "你是一位专业量化交易员的AI助手，负责分析每周交易表现并提供全面的总结。使用客观、分析性的语言，突出主要趋势和战略调整。"
            elif report_type == "monthly":
                system_prompt = "你是一位专业量化交易员的AI助手，负责分析每月交易表现并提供深入的战略分析。使用专业的语言，包含长期趋势和主要调整建议。"
            else:
                system_prompt = "你是一位专业量化交易员的AI助手，负责分析交易表现并提供客观总结。"
            
            # 构建提示
            prompt = f"""
请分析以下交易数据，提供一个简短、专业的{report_type}交易总结，适合语音播报：

交易统计:
- 总盈亏: ${total_pnl:.2f}
- 平均胜率: {avg_win_rate:.2%}
- 总交易次数: {total_trades}
- 运行策略数: {len(df)}

"""
            
            # 添加表现最好和最差的策略
            if 'pnl' in df.columns and not df.empty:
                best_strategy = df.loc[df['pnl'].idxmax()]
                worst_strategy = df.loc[df['pnl'].idxmin()]
                prompt += f"""
表现最佳策略:
- {best_strategy.get('name', 'Unknown')}: ${best_strategy.get('pnl', 0):.2f}

表现欠佳策略:
- {worst_strategy.get('name', 'Unknown')}: ${worst_strategy.get('pnl', 0):.2f}
"""
            
            # 添加市场数据（如果有）
            if market_data:
                prompt += "\n市场数据:\n"
                for key, value in market_data.items():
                    prompt += f"- {key}: {value}\n"
            
            prompt += """
要求:
1. 总结限制在80字以内
2. 客观、专业的语言
3. 重点突出总盈亏和关键表现
4. 包含一条简短的建议或观察
5. 格式适合语音播报
"""
            
            # 调用DeepSeek API
            summary = get_deepseek_response(
                prompt=prompt,
                api_key=self.deepseek_api_key,
                max_tokens=150,
                temperature=0.3,
                system_prompt=system_prompt
            )
            
            return summary
        except Exception as e:
            logger.error(f"生成AI摘要时出错: {str(e)}")
            return f"无法生成AI摘要: {str(e)}"
    
    def _save_report_to_file(self, report_data: Dict[str, Any], report_type: str) -> str:
        """
        保存报告到文件
        
        Args:
            report_data: 报告数据
            report_type: 报告类型
            
        Returns:
            保存的文件路径
        """
        try:
            # 创建文件名
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"{report_type}_report_{date_str}.json"
            file_path = str(self.reports_dir / filename)
            
            # 写入JSON文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"报告已保存到: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"保存报告到文件时出错: {str(e)}")
            return ""
    
    def _send_report_notification(self, report_data: Dict[str, Any], report_type: str):
        """
        发送报告通知
        
        Args:
            report_data: 报告数据
            report_type: 报告类型
        """
        try:
            # 1. 发送文本摘要
            caption_map = {
                "daily": "📊 每日交易报告",
                "weekly": "📈 每周交易报告",
                "monthly": "📑 每月交易报告"
            }
            caption = caption_map.get(report_type, "交易报告")
            
            # 构建通知文本
            summary_text = (
                f"{caption}\n\n"
                f"总盈亏: ${report_data.get('total_pnl', 0):.2f}\n"
                f"胜率: {report_data.get('avg_win_rate', 0):.2%}\n"
                f"交易次数: {report_data.get('total_trades', 0)}\n"
                f"策略数量: {report_data.get('strategies_count', 0)}\n\n"
                f"最佳策略: {report_data.get('best_strategy', 'N/A')} (${report_data.get('best_strategy_pnl', 0):.2f})\n"
                f"表现欠佳: {report_data.get('worst_strategy', 'N/A')} (${report_data.get('worst_strategy_pnl', 0):.2f})\n\n"
                f"AI总结:\n{report_data.get('summary', 'N/A')}"
            )
            
            # 发送文本摘要
            notifier.send_text(summary_text, level="DAILY")
            
            # 2. 发送图表
            charts = report_data.get("charts", [])
            for chart in charts:
                chart_path = chart.get("path")
                chart_type = chart.get("type")
                
                if chart_path and os.path.exists(chart_path):
                    chart_caption = f"{caption} - {chart_type.capitalize()}"
                    notifier.send_image(chart_path, caption=chart_caption, level="DAILY")
            
            # 3. 发送语音摘要
            voice_summarizer.generate_and_send_voice_summary(
                raw_text=summary_text,
                summary_type="market_close" if report_type == "daily" else "trading_day",
                caption=f"🔊 {caption}语音摘要",
                notification_level="DAILY",
                max_tokens=100
            )
            
            logger.info(f"{report_type.capitalize()}报告通知已发送")
        except Exception as e:
            logger.error(f"发送报告通知时出错: {str(e)}")
    
    def _add_to_history(self, report_data: Dict[str, Any]):
        """添加报告到历史记录"""
        self.report_history.append(report_data)
        
        # 保持历史记录在最大大小以内
        if len(self.report_history) > self.max_history_size:
            self.report_history = self.report_history[-self.max_history_size:]
    
    def get_latest_report(self, report_type: str = "daily") -> Optional[Dict[str, Any]]:
        """
        获取最新报告
        
        Args:
            report_type: 报告类型
        
        Returns:
            最新报告数据
        """
        # 按时间戳倒序排序，找出指定类型的最新报告
        for report in reversed(self.report_history):
            if report.get("report_type") == report_type:
                return report
        
        return None
    
    def generate_report_on_schedule(self, 
                                  strategies_data_provider: Callable, 
                                  market_data_provider: Optional[Callable] = None,
                                  report_type: str = "daily"):
        """
        按计划生成报告
        
        Args:
            strategies_data_provider: 提供策略数据的函数
            market_data_provider: 提供市场数据的函数，可选
            report_type: 报告类型
        """
        try:
            # 获取策略数据
            strategies_data = strategies_data_provider()
            
            # 获取市场数据（如果提供了相应函数）
            market_data = market_data_provider() if market_data_provider else None
            
            # 生成报告
            self.generate_daily_report(strategies_data, market_data, report_type)
            
        except Exception as e:
            logger.error(f"按计划生成报告时出错: {str(e)}")

# 单例模式，方便直接导入使用
daily_reporter = AIDailyReporter()

# 测试代码
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 测试数据
    test_strategies_data = [
        {
            "name": "Mean Reversion",
            "pnl": 340.50,
            "win_rate": 0.65,
            "trades": 20,
            "max_drawdown": 120.30,
            "pnl_series": [50, -30, 80, 120, -20, 70, 150, -80]
        },
        {
            "name": "Gamma Scalping",
            "pnl": 520.75,
            "win_rate": 0.72,
            "trades": 25,
            "max_drawdown": 90.50,
            "pnl_series": [80, 120, -50, 90, 130, 150, -40, 40]
        },
        {
            "name": "Breakout V2",
            "pnl": -120.25,
            "win_rate": 0.40,
            "trades": 15,
            "max_drawdown": 200.10,
            "pnl_series": [-40, -60, 30, -50, 70, -70, -10, 10]
        }
    ]
    
    test_market_data = {
        "spy_change": "+0.5%",
        "vix": "14.3",
        "market_sentiment": "中性偏多",
        "sector_performance": "科技+1.2%, 金融-0.3%",
        "notable_events": "无重大事件"
    }
    
    # 生成测试报告
    report_result = daily_reporter.generate_daily_report(
        test_strategies_data,
        test_market_data,
        report_type="daily",
        send_notification=True
    )
    
    print(f"报告生成结果: {'成功' if report_result.get('success', False) else '失败'}")
    print(f"AI总结:\n{report_result.get('summary', 'N/A')}")
    print(f"生成的图表: {len(report_result.get('charts', []))}") 