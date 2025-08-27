"""


AI智能策略辅助工具


集成DeepSeek API生成和优化交易策略


"""


import os


import json


import logging


import pandas as pd


from datetime import datetime


from .deepseek_api import get_deepseek_response





logger = logging.getLogger(__name__)





# 策略提示模板 - 用于指导AI生成交易策略


STRATEGY_PROMPT_TEMPLATE = """


你是一个专业的量化交易策略分析师。请根据以下市场数据和技术指标，生成一个交易策略建议:





{market_data}





基于上述数据，请提供:





1. 市场趋势分析: 分析当前趋势方向和强度


2. 关键支撑/阻力位: 确定重要价格水平


3. 交易信号: 明确指出是买入、卖出还是持有信号，以及信号强度(1-10)


4. 建议的入场价格范围


5. 止损价位


6. 目标价格


7. 风险评级(低/中/高)





请给出简明扼要的分析，重点突出实际可执行的交易策略。


"""





class AIStrategyGenerator:


    """使用DeepSeek API生成交易策略的工具类"""


    


    def __init__(self, api_key=None):


        """


        初始化策略生成器


        


        参数:


            api_key (str): DeepSeek API密钥，默认从环境变量获取


        """


        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")


    


    def generate_strategy(self, symbol, price_data, indicators, timeframe="daily"):


        """


        生成交易策略


        


        参数:


            symbol (str): 股票代码


            price_data (pd.DataFrame): 价格历史数据


            indicators (dict): 技术指标


            timeframe (str): 时间周期(daily, weekly, intraday等)


            


        返回:


            dict: 包含策略分析和建议的字典


        """


        # 格式化市场数据


        market_data = self._format_market_data(symbol, price_data, indicators, timeframe)


        


        # 构建提示词


        prompt = STRATEGY_PROMPT_TEMPLATE.format(market_data=market_data)


        


        # 调用API获取策略


        system_prompt = "你是一位资深量化分析师，擅长基于市场数据生成交易策略。请保持客观、精确，并提供可执行的交易建议。"


        strategy_text = get_deepseek_response(prompt, api_key=self.api_key, 


                                            system_prompt=system_prompt, 


                                            max_tokens=1000,


                                            temperature=0.3)


        


        # 解析策略结果


        result = {


            "symbol": symbol,


            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),


            "timeframe": timeframe,


            "strategy_text": strategy_text,


            "raw": {


                "market_data": market_data,


                "prompt": prompt


            }


        }


        


        # 尝试提取结构化信号


        signal = self._extract_signal_from_text(strategy_text, symbol)


        if signal:


            result.update(signal)


        


        return result


    


    def evaluate_existing_strategy(self, strategy_description, market_data, historical_performance=None):


        """


        评估现有交易策略


        


        参数:


            strategy_description (str): 策略描述


            market_data (dict): 当前市场数据


            historical_performance (dict, optional): 历史表现数据


            


        返回:


            dict: 策略评估结果


        """


        # 构建评估提示词


        prompt = f"""


        请评估以下交易策略在当前市场环境下的有效性和风险:


        


        策略描述:


        {strategy_description}


        


        当前市场情况:


        {json.dumps(market_data, indent=2, ensure_ascii=False)}


        """


        


        if historical_performance:


            prompt += f"""


            历史表现:


            - 胜率: {historical_performance.get('win_rate', 'N/A')}


            - 平均收益: {historical_performance.get('avg_return', 'N/A')}


            - 最大回撤: {historical_performance.get('max_drawdown', 'N/A')}


            - 夏普比率: {historical_performance.get('sharpe_ratio', 'N/A')}


            """


        


        prompt += """


        请提供以下评估:


        1. 策略在当前市场的适用性评分(1-10)


        2. 风险评级(低/中/高)


        3. 优势分析


        4. 劣势分析


        5. 改进建议


        6. 预期表现


        """


        


        # 调用API获取评估


        system_prompt = "你是一位策略评估专家，擅长评估交易策略在不同市场环境下的有效性。请给出客观、公正的评估。"


        evaluation = get_deepseek_response(prompt, api_key=self.api_key, 


                                         system_prompt=system_prompt,


                                         max_tokens=1000,


                                         temperature=0.4)


        


        return {


            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),


            "strategy": strategy_description,


            "evaluation": evaluation


        }


    


    def optimize_strategy(self, original_strategy, market_data, performance_issues=None, risk_tolerance="medium"):


        """


        优化现有交易策略


        


        参数:


            original_strategy (str): 原始策略描述


            market_data (str): 市场数据


            performance_issues (list, optional): 性能问题列表


            risk_tolerance (str): 风险承受能力("low", "medium", "high")


            


        返回:


            dict: 优化建议


        """


        # 构建优化提示词


        prompt = f"""


        请优化以下交易策略，使其更适合当前市场环境，并符合{risk_tolerance}风险偏好:


        


        原始策略:


        {original_strategy}


        


        当前市场数据:


        {market_data}


        """


        


        if performance_issues:


            prompt += "\n存在的问题:\n"


            for issue in performance_issues:


                prompt += f"- {issue}\n"


        


        prompt += f"""


        请提供:


        1. 优化后的完整策略描述


        2. 关键参数调整(如止损点、目标价格、入场条件等)


        3. 优化理由


        4. 预期改进效果


        


        注意保持策略的核心逻辑，同时对参数和条件进行优化，以提高在当前市场环境的表现。


        """


        


        # 调用API获取优化建议


        system_prompt = "你是一位策略优化专家，擅长根据市场变化调整和优化交易策略。请给出具体、可执行的优化建议。"


        optimization = get_deepseek_response(prompt, api_key=self.api_key, 


                                           system_prompt=system_prompt,


                                           max_tokens=1200,


                                           temperature=0.4)


        


        return {


            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),


            "original_strategy": original_strategy,


            "optimization": optimization


        }


    


    def _format_market_data(self, symbol, price_data, indicators, timeframe):


        """格式化市场数据为文本格式"""


        # 获取最近的价格数据


        recent_data = price_data.tail(10)  # 最近10个周期的数据


        latest = price_data.iloc[-1]


        


        # 基本信息


        result = f"股票: {symbol}\n"


        result += f"时间周期: {timeframe}\n"


        result += f"当前价格: {latest['close']}\n"


        result += f"52周最高: {price_data['high'].max()}\n"


        result += f"52周最低: {price_data['low'].min()}\n\n"


        


        # 最近价格走势


        result += "最近价格数据:\n"


        for date, row in recent_data.iterrows():


            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)


            result += f"{date_str}: 开盘 {row['open']:.2f}, 最高 {row['high']:.2f}, 最低 {row['low']:.2f}, 收盘 {row['close']:.2f}"


            if 'volume' in row:


                result += f", 成交量 {row['volume']}\n"


            else:


                result += "\n"


        


        # 技术指标


        if indicators:


            result += "\n技术指标:\n"


            for name, value in indicators.items():


                result += f"- {name}: {value}\n"


        


        return result


    


    def _extract_signal_from_text(self, strategy_text, symbol):


        """尝试从策略文本中提取结构化的交易信号"""


        # 构建提示词，要求AI解析策略文本并提取关键信息


        prompt = f"""


        请解析以下交易策略文本，提取关键信息并以JSON格式返回:


        


        {strategy_text}


        


        请提取以下字段(如果存在):


        - signal_type: 信号类型，必须是以下之一: "buy", "sell", "hold"


        - confidence: 信号强度或置信度，1-10的数字


        - entry_price_low: 建议入场价格下限


        - entry_price_high: 建议入场价格上限


        - stop_loss: 止损价格


        - target_price: 目标价格


        - risk_level: 风险等级，必须是以下之一: "low", "medium", "high"


        - trend: 市场趋势，必须是以下之一: "bullish", "bearish", "neutral", "ranging"


        


        以有效的JSON格式返回结果，只返回JSON，不要有其他文本。


        如果无法从文本中提取某个字段，则将该字段设为null。


        """


        


        try:


            # 调用API提取结构化信号


            extraction_result = get_deepseek_response(prompt, api_key=self.api_key, temperature=0.1)


            


            # 尝试解析JSON


            signal = json.loads(extraction_result)


            


            # 添加股票代码


            signal["symbol"] = symbol


            


            return signal


        except Exception as e:


            logger.warning(f"无法从策略文本中提取结构化信号: {e}")


            return None








# 测试代码


if __name__ == "__main__":


    # 创建示例价格数据


    dates = pd.date_range(end=datetime.now().date(), periods=30)


    prices = pd.DataFrame({


        'open': [150 + i * 0.5 + ((-1)**i) for i in range(30)],


        'high': [153 + i * 0.5 + ((-1)**i) * 2 for i in range(30)],


        'low': [148 + i * 0.5 - ((-1)**i) for i in range(30)],


        'close': [151 + i * 0.5 for i in range(30)],


        'volume': [30000000 + ((-1)**i) * 5000000 for i in range(30)]


    }, index=dates)


    


    # 创建示例技术指标


    indicators = {


        "RSI(14)": 56.8,


        "MACD": 1.25,


        "Signal Line": 0.75,


        "MA(50)": 145.3,


        "MA(200)": 138.7,


        "Bollinger Bands": "上轨: 158.3, 中轨: 151.2, 下轨: 144.1",


        "Stochastic %K": 70.5,


        "Stochastic %D": 65.2


    }


    


    # 测试策略生成


    generator = AIStrategyGenerator()


    strategy = generator.generate_strategy("SPY", prices, indicators, "daily")


    


    print("===== 生成的策略 =====")


    print(strategy['strategy_text'])


    


    # 如果成功提取了结构化信号


    if 'signal_type' in strategy:


        print("\n===== 提取的交易信号 =====")


        signal_info = {k: v for k, v in strategy.items() if k not in ['strategy_text', 'raw', 'timestamp']}


        print(json.dumps(signal_info, indent=2, ensure_ascii=False)) 