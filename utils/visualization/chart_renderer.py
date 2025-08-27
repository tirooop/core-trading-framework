"""


图表渲染模块





为AI量化社区平台提供图表渲染功能，支持:


- K线图与各类技术指标


- 组合表现图表


- 策略回测图表


- 市场分析图表


"""





import os


import logging


import numpy as np


import pandas as pd


import matplotlib.pyplot as plt


import matplotlib.dates as mdates


from datetime import datetime, timedelta


import mplfinance as mpf


from typing import Dict, List, Tuple, Optional, Any, Union


import io


import yfinance as yf





# 配置日志


logger = logging.getLogger(__name__)





class ChartRenderer:


    """图表渲染器，生成各类图表"""


    


    def __init__(self, 


                 output_dir: str = "static/charts",


                 default_style: str = "yahoo",


                 dpi: int = 100):


        """


        初始化图表渲染器


        


        Args:


            output_dir: 图表输出目录


            default_style: 默认图表样式


            dpi: 图像分辨率


        """


        self.output_dir = output_dir


        self.default_style = default_style


        self.dpi = dpi


        


        # 创建输出目录


        os.makedirs(output_dir, exist_ok=True)


        


        # 设置默认绘图样式


        plt.style.use('ggplot')


        


        logger.info(f"图表渲染器初始化完成，输出目录: {output_dir}")


        


    def render_candlestick(self, 


                          symbol: str,


                          data: Optional[pd.DataFrame] = None,


                          period: str = "1mo",


                          interval: str = "1d",


                          indicators: List[str] = None,


                          title: Optional[str] = None,


                          save_path: Optional[str] = None) -> str:


        """


        绘制K线图


        


        Args:


            symbol: 股票代码


            data: 可选的预加载数据，如果为None则自动获取


            period: 数据周期 (例如: 1d, 1mo, 3mo, 1y)


            interval: 数据间隔 (例如: 1m, 5m, 15m, 1h, 1d, 1wk)


            indicators: 要添加的指标列表 (例如: ['sma', 'ema', 'macd', 'rsi'])


            title: 图表标题，默认使用symbol


            save_path: 自定义保存路径，默认使用output_dir


            


        Returns:


            保存的图表文件路径


        """


        # 加载数据


        if data is None:


            try:


                data = yf.download(symbol, period=period, interval=interval)


                if data.empty:


                    logger.error(f"无法获取 {symbol} 的数据")


                    return ""


            except Exception as e:


                logger.error(f"获取 {symbol} 数据时出错: {str(e)}")


                return ""


            


        # 准备指标


        if indicators is None:


            indicators = ['sma', 'bb']


        


        add_plot = []


        if 'sma' in indicators:


            # 添加简单移动平均线


            sma20 = mpf.make_addplot(data['Close'].rolling(window=20).mean(), color='blue', width=0.7)


            sma50 = mpf.make_addplot(data['Close'].rolling(window=50).mean(), color='red', width=0.7)


            add_plot.extend([sma20, sma50])


        


        if 'ema' in indicators:


            # 添加指数移动平均线


            ema12 = mpf.make_addplot(data['Close'].ewm(span=12, adjust=False).mean(), color='green', width=0.7)


            ema26 = mpf.make_addplot(data['Close'].ewm(span=26, adjust=False).mean(), color='purple', width=0.7)


            add_plot.extend([ema12, ema26])


            


        if 'bb' in indicators:


            # 添加布林带


            bb_period = 20


            std_multiplier = 2


            


            sma = data['Close'].rolling(window=bb_period).mean()


            std = data['Close'].rolling(window=bb_period).std()


            


            upper_band = sma + (std * std_multiplier)


            lower_band = sma - (std * std_multiplier)


            


            add_plot.extend([


                mpf.make_addplot(upper_band, color='rgba(0,0,255,0.3)', width=0.7),


                mpf.make_addplot(lower_band, color='rgba(0,0,255,0.3)', width=0.7)


            ])


            


        if 'rsi' in indicators:


            # 计算RSI


            delta = data['Close'].diff()


            gain = delta.where(delta > 0, 0)


            loss = -delta.where(delta < 0, 0)


            


            avg_gain = gain.rolling(window=14).mean()


            avg_loss = loss.rolling(window=14).mean()


            


            rs = avg_gain / avg_loss


            rsi = 100 - (100 / (1 + rs))


            


            # 添加RSI面板


            add_plot.append(


                mpf.make_addplot(rsi, panel=2, color='purple', width=0.8, ylabel='RSI')


            )


            


        # 设置样式


        style = mpf.make_mpf_style(base_mpf_style=self.default_style, 


                                  marketcolors=mpf.make_marketcolors(


                                      up='red', down='green', 


                                      wick={'up': 'red', 'down': 'green'},


                                      edge={'up': 'red', 'down': 'green'},


                                      volume={'up': 'red', 'down': 'green'}


                                  ))


        


        # 设置标题


        if title is None:


            title = f"{symbol} {interval} 图表"


            


        # 准备保存路径


        if save_path is None:


            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


            filename = f"{symbol}_{interval}_{timestamp}.png"


            save_path = os.path.join(self.output_dir, filename)


        


        # 绘制图表


        fig, axes = mpf.plot(


            data,


            type='candle',


            style=style,


            addplot=add_plot,


            volume=True,


            figsize=(12, 8),


            panel_ratios=(4, 1),


            tight_layout=True,


            returnfig=True,


            title=title


        )


        


        # 保存图表


        fig.savefig(save_path, dpi=self.dpi)


        plt.close(fig)


        


        logger.info(f"K线图已保存: {save_path}")


        return save_path


    


    def render_portfolio(self,


                        portfolio_data: Dict[str, Any],


                        title: str = "投资组合表现",


                        save_path: Optional[str] = None) -> str:


        """


        绘制投资组合表现图表


        


        Args:


            portfolio_data: 投资组合数据


            title: 图表标题


            save_path: 自定义保存路径


            


        Returns:


            保存的图表文件路径


        """


        # 解析投资组合数据


        if 'performance' not in portfolio_data or 'assets' not in portfolio_data:


            logger.error("投资组合数据格式不正确")


            return ""


            


        performance = portfolio_data['performance']


        assets = portfolio_data['assets']


        


        # 创建图表


        fig, axes = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1]})


        


        # 绘制投资组合价值图


        if 'dates' in performance and 'values' in performance:


            dates = pd.to_datetime(performance['dates'])


            values = performance['values']


            


            axes[0].plot(dates, values, 'b-', linewidth=2)


            axes[0].set_title(title)


            axes[0].set_ylabel('投资组合价值')


            axes[0].grid(True)


            axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))


            


            # 计算和绘制基准比较(如有)


            if 'benchmark' in performance and 'benchmark_values' in performance:


                benchmark = performance['benchmark']


                benchmark_values = performance['benchmark_values']


                


                axes[0].plot(dates, benchmark_values, 'r--', linewidth=1.5, label=benchmark)


                axes[0].legend()


                


        # 绘制资产分配饼图


        if isinstance(assets, list) and len(assets) > 0:


            labels = [asset['symbol'] for asset in assets]


            weights = [asset['weight'] * 100 for asset in assets]  # 转换为百分比


            


            axes[1].pie(weights, labels=labels, autopct='%1.1f%%', startangle=90)


            axes[1].set_title('资产配置')


            axes[1].axis('equal')


        


        # 调整布局


        plt.tight_layout()


        


        # 准备保存路径


        if save_path is None:


            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


            filename = f"portfolio_{timestamp}.png"


            save_path = os.path.join(self.output_dir, filename)


            


        # 保存图表


        plt.savefig(save_path, dpi=self.dpi)


        plt.close(fig)


        


        logger.info(f"投资组合图表已保存: {save_path}")


        return save_path


    


    def render_strategy_backtest(self,


                                backtest_data: Dict[str, Any],


                                title: Optional[str] = None,


                                save_path: Optional[str] = None) -> str:


        """


        绘制策略回测结果图表


        


        Args:


            backtest_data: 回测数据


            title: 图表标题


            save_path: 自定义保存路径


            


        Returns:


            保存的图表文件路径


        """


        # 解析回测数据


        if 'equity_curve' not in backtest_data or 'trades' not in backtest_data:


            logger.error("回测数据格式不正确")


            return ""


            


        equity_curve = backtest_data['equity_curve']


        trades = backtest_data['trades']


        metrics = backtest_data.get('metrics', {})


        strategy_name = backtest_data.get('strategy_name', '未命名策略')


        


        # 如果没有指定标题，使用策略名称


        if title is None:


            title = f"{strategy_name} 回测结果"


            


        # 创建图表


        fig, axes = plt.subplots(3, 1, figsize=(12, 12), gridspec_kw={'height_ratios': [3, 1, 1]})


        


        # 绘制权益曲线


        if isinstance(equity_curve, dict) and 'dates' in equity_curve and 'values' in equity_curve:


            dates = pd.to_datetime(equity_curve['dates'])


            values = equity_curve['values']


            


            axes[0].plot(dates, values, 'b-', linewidth=2)


            axes[0].set_title(title)


            axes[0].set_ylabel('账户价值')


            axes[0].grid(True)


            axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))


            


            # 添加基准比较(如有)


            if 'benchmark' in equity_curve and 'benchmark_values' in equity_curve:


                benchmark = equity_curve['benchmark']


                benchmark_values = equity_curve['benchmark_values']


                


                axes[0].plot(dates, benchmark_values, 'r--', linewidth=1.5, label=benchmark)


                axes[0].legend()


                


            # 计算和绘制回撤


            if len(values) > 0:


                # 计算最大回撤


                cummax = np.maximum.accumulate(values)


                drawdown = (values - cummax) / cummax


                


                axes[1].fill_between(dates, drawdown * 100, 0, color='red', alpha=0.3)


                axes[1].set_title('回撤 (%)')


                axes[1].set_ylabel('回撤 %')


                axes[1].grid(True)


                axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))


        


        # 绘制交易统计


        if isinstance(trades, list) and len(trades) > 0:


            # 提取交易收益


            profits = [trade.get('profit', 0) for trade in trades]


            


            # 绘制交易收益柱状图


            axes[2].bar(range(len(profits)), profits, color=['green' if p >= 0 else 'red' for p in profits])


            axes[2].set_title('交易收益')


            axes[2].set_xlabel('交易序号')


            axes[2].set_ylabel('收益')


            axes[2].grid(True)


            


        # 添加关键指标标注


        if metrics:


            info_text = (


                f"总收益: {metrics.get('total_return', 0):.2%}  "


                f"年化收益: {metrics.get('annual_return', 0):.2%}  "


                f"夏普比率: {metrics.get('sharpe_ratio', 0):.2f}\n"


                f"最大回撤: {metrics.get('max_drawdown', 0):.2%}  "


                f"胜率: {metrics.get('win_rate', 0):.2%}  "


                f"交易次数: {metrics.get('trades_count', 0)}"


            )


            


            fig.text(0.5, 0.01, info_text, ha='center', fontsize=12, 


                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))


            


        # 调整布局


        plt.tight_layout(rect=[0, 0.03, 1, 0.97])


        


        # 准备保存路径


        if save_path is None:


            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


            filename = f"backtest_{timestamp}.png"


            save_path = os.path.join(self.output_dir, filename)


            


        # 保存图表


        plt.savefig(save_path, dpi=self.dpi)


        plt.close(fig)


        


        logger.info(f"回测结果图表已保存: {save_path}")


        return save_path


    


    def render_market_analysis(self,


                              market_data: Dict[str, Any],


                              title: str = "市场分析",


                              save_path: Optional[str] = None) -> str:


        """


        绘制市场分析图表


        


        Args:


            market_data: 市场数据


            title: 图表标题


            save_path: 自定义保存路径


            


        Returns:


            保存的图表文件路径


        """


        # 解析市场数据


        if 'sectors' not in market_data and 'correlations' not in market_data:


            logger.error("市场数据格式不正确")


            return ""


            


        # 创建图表


        fig, axes = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [1, 1]})


        


        # 绘制板块表现


        if 'sectors' in market_data and isinstance(market_data['sectors'], dict):


            sectors = market_data['sectors']


            names = list(sectors.keys())


            performances = [sectors[name] * 100 for name in names]  # 转换为百分比


            


            # 按表现排序


            sorted_indices = np.argsort(performances)


            sorted_names = [names[i] for i in sorted_indices]


            sorted_performances = [performances[i] for i in sorted_indices]


            


            # 设置颜色


            colors = ['green' if p >= 0 else 'red' for p in sorted_performances]


            


            # 绘制水平条形图


            axes[0].barh(sorted_names, sorted_performances, color=colors)


            axes[0].set_title('板块表现 (%)')


            axes[0].set_xlabel('表现 (%)')


            axes[0].grid(True, axis='x')


            


            # 添加数值标签


            for i, p in enumerate(sorted_performances):


                axes[0].text(p + np.sign(p) * 0.5, i, f'{p:.2f}%', 


                           va='center', ha='left' if p >= 0 else 'right')


                


        # 绘制相关性热图


        if 'correlations' in market_data and isinstance(market_data['correlations'], dict):


            correlations = market_data['correlations']


            symbols = list(correlations.keys())


            


            # 构建相关性矩阵


            corr_matrix = np.zeros((len(symbols), len(symbols)))


            for i, sym1 in enumerate(symbols):


                for j, sym2 in enumerate(symbols):


                    if sym2 in correlations[sym1]:


                        corr_matrix[i, j] = correlations[sym1][sym2]


                    else:


                        corr_matrix[i, j] = 0.0


            


            # 绘制热图


            im = axes[1].imshow(corr_matrix, cmap='coolwarm', vmin=-1, vmax=1)


            axes[1].set_title('资产相关性')


            


            # 添加坐标标签


            axes[1].set_xticks(np.arange(len(symbols)))


            axes[1].set_yticks(np.arange(len(symbols)))


            axes[1].set_xticklabels(symbols)


            axes[1].set_yticklabels(symbols)


            


            # 旋转x轴标签


            plt.setp(axes[1].get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")


            


            # 添加颜色条


            cbar = fig.colorbar(im, ax=axes[1])


            cbar.set_label('相关系数')


            


            # 添加数值标签


            for i in range(len(symbols)):


                for j in range(len(symbols)):


                    text = axes[1].text(j, i, f'{corr_matrix[i, j]:.2f}',


                                      ha="center", va="center", color="black" if abs(corr_matrix[i, j]) < 0.5 else "white")


            


        # 调整布局


        plt.tight_layout()


        


        # 准备保存路径


        if save_path is None:


            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


            filename = f"market_analysis_{timestamp}.png"


            save_path = os.path.join(self.output_dir, filename)


            


        # 保存图表


        plt.savefig(save_path, dpi=self.dpi)


        plt.close(fig)


        


        logger.info(f"市场分析图表已保存: {save_path}")


        return save_path


        


    def render_to_bytes(self, 


                       render_func: callable, 


                       *args, **kwargs) -> bytes:


        """


        将图表渲染为字节流，用于内存中传输


        


        Args:


            render_func: 要调用的渲染函数


            *args, **kwargs: 传递给渲染函数的参数


            


        Returns:


            图表的字节流


        """


        # 创建内存缓冲区


        buf = io.BytesIO()


        


        # 临时替换保存路径


        original_save_path = kwargs.get('save_path')


        kwargs['save_path'] = buf


        


        # 调用渲染函数


        try:


            render_func(*args, **kwargs)


        finally:


            # 恢复原始保存路径


            if original_save_path is not None:


                kwargs['save_path'] = original_save_path


        


        # 获取字节流


        buf.seek(0)


        return buf.getvalue() 