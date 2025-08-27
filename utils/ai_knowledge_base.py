import json
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AIKnowledgeBase")

class AIKnowledgeBase:
    """
    AI知识库
    用于存储和分析历史交易信号，实现自我学习和性能分析
    """
    
    def __init__(self, data_dir: str = "data/knowledge_base"):
        """
        初始化AI知识库
        
        Args:
            data_dir: 知识库数据存储目录
        """
        self.data_dir = data_dir
        
        # 确保目录存在
        os.makedirs(data_dir, exist_ok=True)
        
        # 信号历史缓存
        self._signal_cache = {}
        
        # 加载现有数据
        self._load_data()
        
    def _load_data(self):
        """加载现有知识库数据"""
        try:
            # 加载信号历史
            signals_path = os.path.join(self.data_dir, "signals_history.json")
            if os.path.exists(signals_path):
                with open(signals_path, 'r') as f:
                    self._signal_cache = json.load(f)
                logger.info(f"已加载 {len(self._signal_cache)} 条历史信号记录")
            else:
                logger.info("未找到历史信号记录，将创建新的知识库")
                
        except Exception as e:
            logger.error(f"加载知识库数据失败: {str(e)}")
    
    def save_signals(self, signals: List[Dict[str, Any]], date_str: Optional[str] = None) -> bool:
        """
        保存交易信号到知识库
        
        Args:
            signals: 信号列表
            date_str: 日期字符串，默认为当前日期
            
        Returns:
            是否成功保存
        """
        try:
            if not signals:
                logger.warning("没有信号需要保存")
                return False
                
            # 设置日期
            if date_str is None:
                date_str = datetime.now().strftime("%Y-%m-%d")
                
            # 确保每个信号都有时间戳和日期
            for signal in signals:
                if "timestamp" not in signal:
                    signal["timestamp"] = datetime.now().isoformat()
                    
                signal["date"] = date_str
                
            # 添加到缓存
            if date_str in self._signal_cache:
                self._signal_cache[date_str].extend(signals)
            else:
                self._signal_cache[date_str] = signals
                
            # 保存到文件
            signals_path = os.path.join(self.data_dir, "signals_history.json")
            with open(signals_path, 'w') as f:
                json.dump(self._signal_cache, f, indent=2)
                
            logger.info(f"已保存 {len(signals)} 条信号到知识库，日期: {date_str}")
            return True
            
        except Exception as e:
            logger.error(f"保存信号到知识库失败: {str(e)}")
            return False
    
    def save_daily_report(self, report: Dict[str, Any], date_str: Optional[str] = None) -> bool:
        """
        保存每日报告到知识库
        
        Args:
            report: 每日报告数据
            date_str: 日期字符串，默认为当前日期
            
        Returns:
            是否成功保存
        """
        try:
            # 设置日期
            if date_str is None:
                date_str = datetime.now().strftime("%Y-%m-%d")
                
            # 添加日期到报告
            report["date"] = date_str
                
            # 保存到文件
            reports_dir = os.path.join(self.data_dir, "daily_reports")
            os.makedirs(reports_dir, exist_ok=True)
            
            report_path = os.path.join(reports_dir, f"report_{date_str}.json")
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
                
            logger.info(f"已保存每日报告到知识库，日期: {date_str}")
            return True
            
        except Exception as e:
            logger.error(f"保存每日报告到知识库失败: {str(e)}")
            return False
    
    def backtest_signals(self, symbol: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """
        回测历史信号表现
        
        Args:
            symbol: 指定股票代码，None表示所有股票
            days: 回溯天数
            
        Returns:
            回测结果字典
        """
        try:
            # 计算起始日期
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            start_date_str = start_date.strftime("%Y-%m-%d")
            
            # 收集指定日期范围内的信号
            signals = []
            for date_str, date_signals in self._signal_cache.items():
                if date_str >= start_date_str:
                    if symbol:
                        # 过滤特定股票
                        filtered_signals = [s for s in date_signals if s.get("symbol") == symbol]
                        signals.extend(filtered_signals)
                    else:
                        signals.extend(date_signals)
            
            if not signals:
                logger.warning(f"未找到符合条件的历史信号 (symbol={symbol}, days={days})")
                return {
                    "success": False,
                    "message": "未找到符合条件的信号数据",
                    "data": {}
                }
            
            # 数据统计
            total_signals = len(signals)
            bullish_signals = sum(1 for s in signals if s.get("direction", "").upper() == "BULLISH")
            bearish_signals = sum(1 for s in signals if s.get("direction", "").upper() == "BEARISH")
            
            # 按AI评级统计
            rating_a_signals = sum(1 for s in signals if s.get("ai_rating") == "A")
            rating_b_signals = sum(1 for s in signals if s.get("ai_rating") == "B")
            rating_c_signals = sum(1 for s in signals if s.get("ai_rating") == "C")
            
            # 按风险等级统计
            risk_low = sum(1 for s in signals if s.get("risk_level") == "低")
            risk_medium = sum(1 for s in signals if s.get("risk_level") == "中")
            risk_high = sum(1 for s in signals if s.get("risk_level") == "高")
            
            # 置信度统计
            avg_confidence = sum(float(s.get("confidence", 0)) for s in signals) / total_signals
            
            # 按股票统计
            symbols_count = {}
            for signal in signals:
                sym = signal.get("symbol", "Unknown")
                if sym in symbols_count:
                    symbols_count[sym] += 1
                else:
                    symbols_count[sym] = 1
            
            top_symbols = sorted(symbols_count.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # 组装结果
            result = {
                "success": True,
                "period": {
                    "start_date": start_date_str,
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "days": days
                },
                "signals": {
                    "total": total_signals,
                    "bullish": bullish_signals,
                    "bearish": bearish_signals,
                    "bullish_ratio": bullish_signals / total_signals if total_signals > 0 else 0
                },
                "ratings": {
                    "A": rating_a_signals,
                    "B": rating_b_signals,
                    "C": rating_c_signals,
                    "a_ratio": rating_a_signals / total_signals if total_signals > 0 else 0
                },
                "risk_levels": {
                    "低": risk_low,
                    "中": risk_medium,
                    "高": risk_high
                },
                "confidence": {
                    "avg": avg_confidence
                },
                "top_symbols": [{
                    "symbol": symbol,
                    "count": count
                } for symbol, count in top_symbols]
            }
            
            return result
            
        except Exception as e:
            logger.error(f"回测历史信号失败: {str(e)}")
            return {
                "success": False,
                "message": f"回测过程错误: {str(e)}",
                "data": {}
            }
    
    def get_symbol_history(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取特定股票的历史信号
        
        Args:
            symbol: 股票代码
            days: 回溯天数
            
        Returns:
            历史信号列表
        """
        try:
            # 计算起始日期
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            start_date_str = start_date.strftime("%Y-%m-%d")
            
            # 收集信号
            symbol_signals = []
            for date_str, date_signals in self._signal_cache.items():
                if date_str >= start_date_str:
                    filtered_signals = [s for s in date_signals if s.get("symbol") == symbol]
                    symbol_signals.extend(filtered_signals)
            
            # 按时间排序
            symbol_signals.sort(key=lambda x: x.get("timestamp", ""))
            
            return symbol_signals
            
        except Exception as e:
            logger.error(f"获取股票 {symbol} 历史信号失败: {str(e)}")
            return []
    
    def get_historical_performance(self, days: int = 30) -> Dict[str, Any]:
        """
        获取历史性能表现
        
        Args:
            days: 回溯天数
            
        Returns:
            历史性能指标
        """
        # 调用回测方法实现
        return self.backtest_signals(days=days)
    
    def export_to_csv(self, output_path: Optional[str] = None) -> str:
        """
        导出知识库数据到CSV文件
        
        Args:
            output_path: 输出文件路径，默认为知识库目录下的export.csv
            
        Returns:
            导出的文件路径
        """
        try:
            # 准备数据
            data = []
            for date, signals in self._signal_cache.items():
                for signal in signals:
                    data.append({
                        "date": date,
                        "symbol": signal.get("symbol", ""),
                        "direction": signal.get("direction", ""),
                        "confidence": signal.get("confidence", ""),
                        "ai_rating": signal.get("ai_rating", ""),
                        "risk_level": signal.get("risk_level", "")
                    })
            
            if not data:
                logger.warning("没有数据需要导出")
                return ""
                
            # 创建DataFrame
            df = pd.DataFrame(data)
            
            # 确定输出路径
            if output_path is None:
                output_path = os.path.join(self.data_dir, "export.csv")
                
            # 导出到CSV
            df.to_csv(output_path, index=False)
            logger.info(f"已导出 {len(df)} 条记录到 {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"导出数据失败: {str(e)}")
            return ""

    def save_backtest_analysis(self, analysis_result: Dict[str, Any]) -> bool:
        """
        保存回测分析结果到知识库
        
        Args:
            analysis_result: 回测分析结果
            
        Returns:
            是否成功保存
        """
        try:
            # 确保存在存储回测分析的目录
            backtest_dir = os.path.join(self.data_dir, "backtest_analysis")
            os.makedirs(backtest_dir, exist_ok=True)
            
            # 设置文件名（使用策略名称和时间戳）
            strategy_name = analysis_result.get("strategy_name", "unnamed")
            timestamp = analysis_result.get("timestamp", datetime.now().strftime("%Y%m%d%H%M%S"))
            safe_strategy_name = "".join(c if c.isalnum() else "_" for c in strategy_name)
            
            filename = f"{safe_strategy_name}_{timestamp.replace(' ', '_').replace(':', '')}.json"
            file_path = os.path.join(backtest_dir, filename)
            
            # 保存分析结果
            with open(file_path, 'w') as f:
                json.dump(analysis_result, f, indent=2)
                
            logger.info(f"已保存回测分析到知识库: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存回测分析到知识库失败: {str(e)}")
            return False
    
    def query_backtest_patterns(self, strategy_name: Optional[str] = None, 
                               limit: int = 10) -> List[Dict[str, Any]]:
        """
        查询历史回测中识别的失败模式
        
        Args:
            strategy_name: 可选的策略名称过滤条件
            limit: 最大返回数量
            
        Returns:
            模式列表
        """
        try:
            backtest_dir = os.path.join(self.data_dir, "backtest_analysis")
            if not os.path.exists(backtest_dir):
                logger.warning(f"回测分析目录不存在: {backtest_dir}")
                return []
            
            # 获取所有回测分析文件
            results = []
            for filename in os.listdir(backtest_dir):
                if not filename.endswith('.json'):
                    continue
                    
                file_path = os.path.join(backtest_dir, filename)
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        
                    # 过滤策略名称（如果提供）
                    if strategy_name and data.get("strategy_name") != strategy_name:
                        continue
                        
                    # 提取模式分析数据
                    if "pattern_analysis" in data and data["pattern_analysis"]:
                        results.append({
                            "strategy_name": data.get("strategy_name", "未知策略"),
                            "timestamp": data.get("timestamp", ""),
                            "pattern_analysis": data["pattern_analysis"],
                            "key_metrics": {
                                k: v for k, v in data.get("performance_metrics", {}).items()
                                if k in ["sharpe_ratio", "max_drawdown", "win_rate"]
                            }
                        })
                except Exception as e:
                    logger.error(f"读取回测分析文件失败 {file_path}: {str(e)}")
                    continue
            
            # 按时间戳排序（最新的在前）
            results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"查询回测模式失败: {str(e)}")
            return []
    
    def get_strategy_performance_history(self, strategy_name: str) -> List[Dict[str, Any]]:
        """
        获取特定策略的历史性能
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            历史性能记录列表
        """
        try:
            backtest_dir = os.path.join(self.data_dir, "backtest_analysis")
            if not os.path.exists(backtest_dir):
                logger.warning(f"回测分析目录不存在: {backtest_dir}")
                return []
            
            # 获取所有匹配策略名称的回测结果
            results = []
            for filename in os.listdir(backtest_dir):
                if not filename.endswith('.json'):
                    continue
                    
                file_path = os.path.join(backtest_dir, filename)
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        
                    # 过滤策略名称
                    if data.get("strategy_name") != strategy_name:
                        continue
                        
                    # 提取性能指标
                    results.append({
                        "timestamp": data.get("timestamp", ""),
                        "metrics": data.get("performance_metrics", {})
                    })
                except Exception as e:
                    logger.error(f"读取回测分析文件失败 {file_path}: {str(e)}")
                    continue
            
            # 按时间戳排序
            results.sort(key=lambda x: x.get("timestamp", ""))
            
            return results
            
        except Exception as e:
            logger.error(f"获取策略性能历史失败: {str(e)}")
            return [] 