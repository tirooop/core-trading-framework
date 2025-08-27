"""
AI市场分析工具
整合DeepSeek API来提供市场分析和交易建议
"""
import os
import pandas as pd
import logging
from datetime import datetime, timedelta
from .deepseek_api import get_deepseek_response, analyze_market_with_ai

logger = logging.getLogger(__name__)

class AIMarketAnalyzer:
    """使用DeepSeek API进行市场分析的工具类"""
    
    def __init__(self, api_key=None):
        """
        初始化市场分析器
        
        参数:
            api_key (str): DeepSeek API密钥，默认从环境变量获取
        """
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        
    def analyze_stock(self, symbol, price_data, technical_indicators=None, news=None):
        """
        分析股票数据并提供建议
        
        参数:
            symbol (str): 股票代码
            price_data (pd.DataFrame): 价格数据
            technical_indicators (dict, optional): 技术指标数据
            news (list, optional): 相关新闻列表
            
        返回:
            dict: 包含分析结果和建议的字典
        """
        # 整理数据为文本格式
        market_data = self._format_data_for_analysis(symbol, price_data, technical_indicators, news)
        
        # 使用DeepSeek API进行分析
        analysis = analyze_market_with_ai(symbol, market_data)
        
        # 获取具体的交易建议
        trading_prompt = f"基于以下市场分析，请给出明确的交易建议（买入/卖出/持有），以及建议的入场价格区间和止损位置。分析内容:\n\n{analysis}"
        recommendation = get_deepseek_response(trading_prompt, api_key=self.api_key, temperature=0.4)
        
        # 获取风险评估
        risk_prompt = f"针对股票 {symbol}，根据以下市场数据和分析，评估当前交易风险等级(低/中/高)并解释原因:\n\n{market_data}\n\n分析:\n{analysis}"
        risk_assessment = get_deepseek_response(risk_prompt, api_key=self.api_key, temperature=0.4)
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "market_analysis": analysis,
            "trading_recommendation": recommendation,
            "risk_assessment": risk_assessment
        }
    
    def get_market_outlook(self, index_data, economic_indicators=None, timeframe="short-term"):
        """
        获取整体市场展望
        
        参数:
            index_data (dict): 主要指数数据
            economic_indicators (dict, optional): 经济指标
            timeframe (str): 时间框架 ("short-term", "medium-term", "long-term")
            
        返回:
            str: 市场展望分析
        """
        # 构建市场概览数据
        market_overview = f"市场主要指数:\n"
        for idx_name, idx_data in index_data.items():
            market_overview += f"- {idx_name}: 当前 {idx_data['current']}, 变动 {idx_data['change']}%\n"
        
        if economic_indicators:
            market_overview += "\n经济指标:\n"
            for indicator, value in economic_indicators.items():
                market_overview += f"- {indicator}: {value}\n"
        
        # 构建提示词
        prompt = f"""
        请分析以下市场数据，提供{timeframe}市场展望:
        
        {market_overview}
        
        在分析中请考虑:
        1. 市场当前趋势方向
        2. 主要支撑和阻力位
        3. 潜在风险因素
        4. 未来可能的机会
        5. 对投资者的建议
        """
        
        # 调用API获取分析
        system_prompt = "你是一位资深市场策略师，擅长分析市场趋势和提供战略建议。请基于数据给出客观分析。"
        return get_deepseek_response(prompt, api_key=self.api_key, system_prompt=system_prompt, max_tokens=1000)
    
    def analyze_option_strategy(self, symbol, current_price, option_chain, market_view="neutral"):
        """
        分析期权策略
        
        参数:
            symbol (str): 股票代码
            current_price (float): 当前价格
            option_chain (dict): 期权链数据
            market_view (str): 市场观点 ("bullish", "bearish", "neutral")
            
        返回:
            str: 期权策略建议
        """
        # 构建期权数据
        option_data = f"股票: {symbol}\n当前价格: {current_price}\n市场观点: {market_view}\n\n期权链数据:\n"
        for option in option_chain:
            option_data += f"- 类型: {option['type']}, 行权价: {option['strike']}, 价格: {option['price']}, Delta: {option['delta']}, IV: {option['iv']}%\n"
        
        # 构建提示词
        prompt = f"""
        基于以下期权数据和{market_view}市场观点，推荐最适合的期权策略:
        
        {option_data}
        
        请详细说明:
        1. 推荐的期权策略类型(例如:垂直价差、铁鹰、蝶式等)
        2. 具体的执行方式(包括具体选择哪些期权合约)
        3. 最大盈利和最大损失
        4. 盈亏平衡点
        5. 退出策略和风险管理建议
        """
        
        # 调用API获取分析
        system_prompt = "你是一位期权策略专家，精通各种期权组合策略。请基于数据提供具体可执行的策略建议。"
        return get_deepseek_response(prompt, api_key=self.api_key, system_prompt=system_prompt, max_tokens=1200, temperature=0.4)
    
    def _format_data_for_analysis(self, symbol, price_data, technical_indicators=None, news=None):
        """将数据格式化为文本，以便于API分析"""
        # 价格数据摘要
        latest_price = price_data.iloc[-1]
        prev_price = price_data.iloc[-2] if len(price_data) > 1 else None
        
        formatted_data = f"股票: {symbol}\n"
        formatted_data += f"日期: {latest_price.name.strftime('%Y-%m-%d') if hasattr(latest_price.name, 'strftime') else latest_price.name}\n"
        formatted_data += f"开盘价: {latest_price['open']}\n"
        formatted_data += f"最高价: {latest_price['high']}\n"
        formatted_data += f"最低价: {latest_price['low']}\n"
        formatted_data += f"收盘价: {latest_price['close']}\n"
        
        if 'volume' in latest_price:
            formatted_data += f"成交量: {latest_price['volume']}\n"
        
        if prev_price is not None:
            change = latest_price['close'] - prev_price['close']
            pct_change = change / prev_price['close'] * 100
            formatted_data += f"价格变动: {change:.2f} ({pct_change:.2f}%)\n"
        
        # 技术指标
        if technical_indicators:
            formatted_data += "\n技术指标:\n"
            for indicator, value in technical_indicators.items():
                formatted_data += f"- {indicator}: {value}\n"
        
        # 相关新闻
        if news and len(news) > 0:
            formatted_data += "\n相关新闻:\n"
            for item in news[:5]:  # 只使用最近的5条新闻
                formatted_data += f"- {item['title']} ({item['date']})\n"
        
        return formatted_data


# 测试代码
if __name__ == "__main__":
    # 创建示例数据
    sample_data = pd.DataFrame({
        'open': [150.2, 152.8, 151.5, 153.3, 155.2],
        'high': [153.1, 154.0, 152.3, 156.2, 158.7],
        'low': [149.5, 151.2, 149.8, 152.5, 154.3],
        'close': [152.3, 151.8, 152.0, 155.6, 157.8],
        'volume': [32000000, 28000000, 30000000, 40000000, 38000000]
    }, index=pd.date_range(end=datetime.now().date(), periods=5))
    
    # 技术指标
    sample_indicators = {
        "RSI(14)": 62.5,
        "MACD": 2.35,
        "MA(50)": 148.6,
        "MA(200)": 142.3,
        "Bollinger Bands": "上轨: 160.2, 中轨: 151.5, 下轨: 142.8"
    }
    
    # 新闻
    sample_news = [
        {"title": "公司宣布新产品发布", "date": "2023-05-01"},
        {"title": "季度财报超出预期", "date": "2023-04-28"}
    ]
    
    # 测试分析
    analyzer = AIMarketAnalyzer()
    result = analyzer.analyze_stock("AAPL", sample_data, sample_indicators, sample_news)
    
    print("===== 市场分析 =====")
    print(result['market_analysis'])
    print("\n===== 交易建议 =====")
    print(result['trading_recommendation'])
    print("\n===== 风险评估 =====")
    print(result['risk_assessment']) 