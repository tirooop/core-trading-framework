"""
AI Chart Analyzer for generating technical analysis insights using DeepSeek AI.
"""

from utils.deepseek_agent import DeepSeekAgent
from utils.market_data_provider import MarketDataProvider
from utils.technical_indicator_lib import TechnicalIndicatorLib

class AIChartAnalyzer:
    def __init__(self):
        self.agent = DeepSeekAgent(model="deepseek-ai/DeepSeek-V3")
        self.data_provider = MarketDataProvider()
        self.indicators = TechnicalIndicatorLib()
    
    def analyze(self, symbol, days=30, brief=False):
        """
        Generate AI analysis for a stock chart
        
        Args:
            symbol: Stock ticker symbol
            days: Number of days to analyze
            brief: Whether to generate brief (True) or detailed (False) analysis
            
        Returns:
            String with AI analysis of the chart
        """
        try:
            # Fetch market data
            df = self.data_provider.fetch(symbol, days)
            
            # Calculate technical indicators
            df = self.indicators.add_indicators(df)
            
            # Extract key metrics for the prompt
            current_price = df['close'].iloc[-1]
            price_change = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5] * 100
            rsi = df['rsi'].iloc[-1] if 'rsi' in df.columns else "Unknown"
            fisher = df['fisher'].iloc[-1] if 'fisher' in df.columns else "Unknown"
            macd = df['macd'].iloc[-1] if 'macd' in df.columns else "Unknown"
            signal = df['macd_signal'].iloc[-1] if 'macd_signal' in df.columns else "Unknown"
            
            # Get trend information
            trend_direction = self.indicators.get_trend_direction(df)
            trend_strength = self.indicators.get_trend_strength(df)
            
            # Check if price is near Bollinger Bands
            upper_band = df['upper_band'].iloc[-1]
            lower_band = df['lower_band'].iloc[-1]
            band_position = (current_price - lower_band) / (upper_band - lower_band) * 100
            
            # Create prompt for AI
            if brief:
                prompt = self._create_brief_prompt(symbol, current_price, price_change, 
                                                 rsi, trend_direction, band_position)
            else:
                prompt = self._create_detailed_prompt(symbol, current_price, price_change, 
                                                   rsi, fisher, macd, signal, 
                                                   trend_direction, trend_strength, band_position)
            
            # Get AI analysis
            analysis = self.agent.ask(prompt)
            
            return analysis
        
        except Exception as e:
            return f"无法分析 {symbol}：{str(e)}"
    
    def _create_brief_prompt(self, symbol, price, change, rsi, trend, band_position):
        """Create a brief analysis prompt"""
        prompt = f"""
作为专业的量化交易技术分析师，请对{symbol}的技术指标做一个简短的分析。

数据:
- 当前价格: ${price:.2f}
- 5日涨跌幅: {'+' if change >= 0 else ''}{change:.2f}%
- RSI: {rsi:.2f}
- 趋势方向: {trend}
- 布林带位置: {band_position:.2f}%

请提供一个50字左右的简洁分析，包括：
1. 当前趋势状态
2. 可能的支撑/阻力位
3. 操作建议(买入/卖出/持有)
"""
        return prompt
    
    def _create_detailed_prompt(self, symbol, price, change, rsi, fisher, macd, signal, 
                               trend_direction, trend_strength, band_position):
        """Create a detailed analysis prompt"""
        prompt = f"""
作为专业的量化交易技术分析师，请对{symbol}的技术指标做出全面分析。

技术指标数据:
- 当前价格: ${price:.2f}
- 5日涨跌幅: {'+' if change >= 0 else ''}{change:.2f}%
- RSI(14): {rsi:.2f}
- Fisher Transform: {fisher:.4f}
- MACD: {macd:.4f}
- MACD Signal: {signal:.4f}
- 趋势方向: {trend_direction}
- 趋势强度: {trend_strength:.2f}/100
- 布林带位置: {band_position:.2f}% (0%=下轨, 100%=上轨)

请提供详细分析，包括：
1. 当前趋势总结
2. 支撑位和阻力位分析
3. 超买/超卖状态判断
4. 短期（1-3日）价格预测
5. 操作建议（买入/卖出/持有）及理由
6. 潜在风险提示

注意：分析必须围绕技术指标，不要使用基本面因素。保持专业简洁的语言，回答控制在150字以内。
"""
        return prompt 