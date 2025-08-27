"""


AI Backtesting Summarizer - v2.0


Provide intelligent analysis and failure attribution for strategy backtest results


As a key component of AI Quantitative System 6.0


"""


import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from .deepseek_api import get_deepseek_response
from .ai_knowledge_base import AIKnowledgeBase
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 回测分析提示模板


BACKTEST_ANALYSIS_TEMPLATE = """


As a quantitative analysis expert, please provide a detailed analysis of the backtest results for the following trading strategy:





Backtest Parameters:


{backtest_params}





Performance Metrics:


{performance_metrics}





Trade Summary:


{trade_summary}





Please provide the following analysis:





1. Overall performance assessment: Analyze strategy performance based on key indicators (e.g., Sharpe ratio, maximum drawdown, win rate, etc.)


2. Failure attribution analysis: Detailed analysis of the specific reasons and patterns for strategy failure


3. Failure trade characteristic patterns: Analyze whether failure trades exist common characteristics (e.g., specific market conditions, time patterns, etc.)


4. Strategy improvement suggestions: Based on failure attribution, propose specific, implementable improvement solutions


5. Parameter optimization direction: Suggest possible parameter adjustment directions to improve performance





Please provide specific analysis using data support and actionable suggestions.


"""





# 交易类型模式分析模板


TRADE_PATTERN_TEMPLATE = """


Analyze the losing trades in the following trading data to identify possible failure patterns:





Losing Trade Data:


{losing_trades}





Market Environment Data:


{market_conditions}





Please identify the patterns and common characteristics in the losing trades, including:


1. Time pattern: Whether losses are more concentrated in specific time periods


2. Market condition: Whether losses occur in specific market states (e.g., high volatility, trend reversal, etc.)


3. Signal characteristics: Whether the signals causing losses have common features (e.g., signal strength, duration, etc.)


4. Position holding period: Whether the average position holding time of losing trades is significantly different from profitable trades


5. Stop loss characteristics: Analysis of typical scenarios for stop loss triggers





Please provide specific, quantifiable pattern descriptions based on data, avoiding general conclusions.


"""





class AIBacktestSummarizer:


    """AI-powered backtest result summarizer"""


    


    def __init__(self, api_key=None, knowledge_base=None):


        """


        Initialize backtest summarizer


        


        Args:


            api_key (str): DeepSeek API key, defaults to environment variable


            knowledge_base: Knowledge base instance for querying historical backtest results


        """


        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")


        self.knowledge_base = knowledge_base or AIKnowledgeBase()


        self.analysis_history = []


    


    def summarize_backtest(self, backtest_results: Dict[str, Any], market_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:


        """


        Summarize backtest results


        


        Args:


            backtest_results: Backtest results dictionary


            market_data: Optional market data for context analysis


            


        Returns:


            Summary dictionary


        """


        # Build prompt


        prompt = f"""


Backtest Results:


{json.dumps(backtest_results, indent=2)}





Market Data:


{json.dumps(market_data, indent=2) if market_data else "Not provided"}





Please analyze the backtest results and provide:


1. Overall performance summary


2. Key metrics analysis


3. Risk assessment


4. Strategy strengths and weaknesses


5. Improvement suggestions


"""


        


        # Call API


        system_prompt = """You are a professional quantitative strategy analyst, skilled in analyzing trading strategy backtest results and providing failure attribution.


        Your analysis must be data-driven, objective, and specific, avoiding vague conclusions. For identified issues, provide concrete improvement directions."""


        


        analysis = self._call_api(prompt, system_prompt)


        


        return {


            "summary": analysis,


            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),


            "raw_results": backtest_results


        }


    


    def _format_backtest_params(self, strategy_params: Dict[str, Any]) -> str:


        """Format backtest parameters as text format"""


        result = ""


        


        # Basic strategy information


        result += f"Strategy Name: {strategy_params.get('strategy_name', 'Unnamed Strategy')}\n"


        result += f"Asset Class: {strategy_params.get('asset_class', 'Unspecified')}\n"


        result += f"Backtest Period: {strategy_params.get('start_date', 'Unspecified')} to {strategy_params.get('end_date', 'Unspecified')}\n"


        


        # Strategy specific parameters


        if "parameters" in strategy_params:


            result += "\nStrategy Parameters:\n"


            for name, value in strategy_params["parameters"].items():


                result += f"- {name}: {value}\n"


        


        # Risk management parameters


        if "risk_management" in strategy_params:


            result += "\nRisk Management Settings:\n"


            for name, value in strategy_params["risk_management"].items():


                result += f"- {name}: {value}\n"


        


        return result


    


    def _format_performance_metrics(self, backtest_result: Dict[str, Any]) -> str:


        """Format performance metrics as text format"""


        metrics = backtest_result.get("metrics", {})


        result = ""


        


        # Core performance metrics


        result += f"Total Return: {metrics.get('total_return', 0):.2%}\n"


        result += f"Annual Return: {metrics.get('annual_return', 0):.2%}\n"


        result += f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}\n"


        result += f"Maximum Drawdown: {metrics.get('max_drawdown', 0):.2%}\n"


        result += f"Calmar Ratio: {metrics.get('calmar_ratio', 0):.2f}\n"


        


        # Trade statistics


        result += f"\nTrade Statistics:\n"


        result += f"Total Trades: {metrics.get('total_trades', 0)}\n"


        result += f"Winning Trades: {metrics.get('winning_trades', 0)}\n"


        result += f"Losing Trades: {metrics.get('losing_trades', 0)}\n"


        result += f"Win Rate: {metrics.get('win_rate', 0):.2%}\n"


        result += f"Profit Factor: {metrics.get('profit_factor', 0):.2f}\n"


        result += f"Average Profit: {metrics.get('avg_profit', 0):.2%}\n"


        result += f"Average Loss: {metrics.get('avg_loss', 0):.2%}\n"


        result += f"Maximum Consecutive Wins: {metrics.get('max_consecutive_wins', 0)}\n"


        result += f"Maximum Consecutive Losses: {metrics.get('max_consecutive_losses', 0)}\n"


        


        # Risk metrics


        result += f"\nRisk Metrics:\n"


        result += f"Volatility: {metrics.get('volatility', 0):.2%}\n"


        result += f"Sortino Ratio: {metrics.get('sortino_ratio', 0):.2f}\n"


        result += f"Beta: {metrics.get('beta', 0):.2f}\n"


        result += f"Information Ratio: {metrics.get('information_ratio', 0):.2f}\n"


        


        return result


    


    def _format_trade_summary(self, backtest_result: Dict[str, Any]) -> str:


        """Format trade summary as text summary"""


        trades = backtest_result.get("trades", [])


        if not trades:


            return "No trade records"


        


        # Sort trades by performance


        sorted_trades = sorted(trades, key=lambda x: x.get("pnl", 0), reverse=True)


        top_trades = sorted_trades[:5]  # Top 5 trades


        bottom_trades = sorted_trades[-5:]  # Worst 5 trades


        


        result = "Top Trade Samples:\n"


        for i, trade in enumerate(top_trades, 1):


            result += f"{i}. {trade.get('entry_date', 'Unknown')} {trade.get('direction', 'Unknown').upper()} "


            result += f"{trade.get('symbol', 'Unknown')} @ {trade.get('entry_price', 0):.2f}, "


            result += f"Exit @ {trade.get('exit_price', 0):.2f}, "


            result += f"PnL {trade.get('pnl', 0):.2%}, "


            result += f"Holding {trade.get('duration', 0)} days\n"


        


        result += "\nWorst Trade Samples:\n"


        for i, trade in enumerate(bottom_trades, 1):


            result += f"{i}. {trade.get('entry_date', 'Unknown')} {trade.get('direction', 'Unknown').upper()} "


            result += f"{trade.get('symbol', 'Unknown')} @ {trade.get('entry_price', 0):.2f}, "


            result += f"Exit @ {trade.get('exit_price', 0):.2f}, "


            result += f"PnL {trade.get('pnl', 0):.2%}, "


            result += f"Holding {trade.get('duration', 0)} days\n"


        


        # Trade distribution statistics


        result += "\nTrade Distribution Statistics:\n"


        


        # Monthly analysis


        if "monthly_returns" in backtest_result:


            result += "Monthly Performance (Top 5):\n"


            monthly = backtest_result["monthly_returns"]


            for month, value in list(sorted(monthly.items(), key=lambda x: x[1], reverse=True))[:5]:


                result += f"- {month}: {value:.2%}\n"


        


        # Signal type analysis


        if "signal_performance" in backtest_result:


            result += "\nSignal Type Performance:\n"


            for signal, perf in backtest_result["signal_performance"].items():


                result += f"- {signal}: Trade Count {perf.get('count', 0)}, Win Rate {perf.get('win_rate', 0):.2%}, Average PnL {perf.get('avg_return', 0):.2%}\n"


        


        return result


    


    def _has_sufficient_losing_trades(self, backtest_result: Dict[str, Any]) -> bool:


        """Determine if there are enough losing trades for pattern analysis"""


        trades = backtest_result.get("trades", [])


        losing_trades = [t for t in trades if t.get("pnl", 0) < 0]


        return len(losing_trades) >= 5  # At least 5 losing trades are needed


    


    def _analyze_trade_patterns(self, backtest_result: Dict[str, Any], 


                               market_data: Optional[pd.DataFrame] = None) -> Optional[str]:


        """Analyze losing trade patterns"""


        trades = backtest_result.get("trades", [])


        losing_trades = [t for t in trades if t.get("pnl", 0) < 0]


        


        if not losing_trades:


            return None


        


        # Format losing trades


        losing_trades_text = "Losing Trade Details:\n"


        for i, trade in enumerate(losing_trades[:10], 1):  # Limit to top 10 trades, avoid too long prompt


            losing_trades_text += f"{i}. {trade.get('entry_date', 'Unknown')} {trade.get('direction', 'Unknown').upper()} "


            losing_trades_text += f"{trade.get('symbol', 'Unknown')} @ {trade.get('entry_price', 0):.2f}, "


            losing_trades_text += f"Exit @ {trade.get('exit_price', 0):.2f}, "


            losing_trades_text += f"PnL {trade.get('pnl', 0):.2%}, "


            losing_trades_text += f"Holding {trade.get('duration', 0)} days\n"


            if "exit_reason" in trade:


                losing_trades_text += f"    Exit Reason: {trade['exit_reason']}\n"


        


        # Format market environment data (if available)


        market_conditions_text = "Market Environment Data:\n"


        if market_data is not None:


            # Extract market data around each trade time point


            for trade in losing_trades[:5]:  # Only analyze market environment around top 5 losing trades


                entry_date = trade.get("entry_date")


                if entry_date and entry_date in market_data.index:


                    # Get data from 5 trading days before and after the trade


                    idx = market_data.index.get_loc(entry_date)


                    start_idx = max(0, idx - 5)


                    end_idx = min(len(market_data), idx + 5)


                    trade_period = market_data.iloc[start_idx:end_idx]


                    


                    # Add market state description


                    market_conditions_text += f"\nMarket State Around Trade {entry_date}:\n"


                    


                    # Price movement


                    price_change = (trade_period['close'].iloc[-1] / trade_period['close'].iloc[0] - 1) * 100


                    market_conditions_text += f"- Price Change: {price_change:.2f}%\n"


                    


                    # Volatility


                    if 'close' in trade_period.columns:


                        volatility = trade_period['close'].pct_change().std() * 100


                        market_conditions_text += f"- Volatility: {volatility:.2f}%\n"


                    


                    # Volume


                    if 'volume' in trade_period.columns:


                        avg_volume = trade_period['volume'].mean()


                        volume_change = (trade_period['volume'].iloc[-1] / trade_period['volume'].iloc[0] - 1) * 100


                        market_conditions_text += f"- Average Volume: {avg_volume:.0f}, Volume Change: {volume_change:.2f}%\n"


        else:


            market_conditions_text += "No available market environment data\n"


        


        # Build pattern analysis prompt


        prompt = TRADE_PATTERN_TEMPLATE.format(


            losing_trades=losing_trades_text,


            market_conditions=market_conditions_text


        )


        


        # Call API for analysis


        system_prompt = """You are a professional trading pattern analyst, skilled in identifying trading failure patterns and common characteristics.


        Please provide objective analysis based on data, identifying specific failure patterns, avoiding general conclusions."""


        


        return get_deepseek_response(


            prompt=prompt,


            api_key=self.api_key, 


            system_prompt=system_prompt, 


            max_tokens=1200,


            temperature=0.3


        )


    


    def _extract_improvement_suggestions(self, analysis_text: str) -> List[str]:


        """Extract improvement suggestions from analysis text"""


        suggestions = []


        lines = analysis_text.split("\n")


        


        in_suggestion_section = False


        for line in lines:


            # Detect improvement suggestion section


            if "Improvement Suggestions" in line or "Strategy Improvement" in line or "Improvement Direction" in line or "Optimization Suggestions" in line:


                in_suggestion_section = True


                continue


            


            if in_suggestion_section and line.strip() and line.strip()[0] in ['-', '•', '1', '2', '3', '4', '5', '6', '7', '8', '9']:


                # Clean format and add suggestion


                suggestion = line.strip()


                # Remove numbering or list symbols


                if suggestion[0].isdigit() and suggestion[1:3] in ['. ', '、', '. ']:


                    suggestion = suggestion[3:].strip()


                elif suggestion[0] in ['-', '•']:


                    suggestion = suggestion[1:].strip()


                


                suggestions.append(suggestion)


        


        return suggestions


    


    def get_historical_patterns(self, strategy_name: Optional[str] = None) -> List[Dict[str, Any]]:


        """


        Get common failure patterns from historical backtests


        


        Args:


            strategy_name: Optional strategy name filter


            


        Returns:


            List of failure patterns


        """


        if not self.knowledge_base:


            return []


        


        return self.knowledge_base.query_backtest_patterns(strategy_name=strategy_name)


    


    def compare_strategies(self, 


                          results: List[Dict[str, Any]]) -> Dict[str, Any]:


        """


        Compare multiple strategy backtest results


        


        Args:


            results: List of backtest results


            


        Returns:


            Comparison analysis result


        """


        if not results or len(results) < 2:


            return {"error": "At least two strategy results are needed for comparison"}


        


        # Extract key metrics for comparison


        comparison = []


        for result in results:


            strategy_name = result.get("strategy_name", "Unnamed Strategy")


            metrics = result.get("metrics", {})


            


            comparison.append({


                "strategy_name": strategy_name,


                "total_return": metrics.get("total_return", 0),


                "sharpe_ratio": metrics.get("sharpe_ratio", 0),


                "max_drawdown": metrics.get("max_drawdown", 0),


                "win_rate": metrics.get("win_rate", 0),


                "profit_factor": metrics.get("profit_factor", 0)


            })


        


        # Sort, by Sharpe ratio


        sorted_comparison = sorted(comparison, key=lambda x: x["sharpe_ratio"], reverse=True)


        


        return {


            "comparison": sorted_comparison,


            "best_strategy": sorted_comparison[0]["strategy_name"] if sorted_comparison else None,


            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")


        } 