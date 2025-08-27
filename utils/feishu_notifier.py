import os


import json


import requests


from io import BytesIO


import base64


import matplotlib.pyplot as plt


from datetime import datetime


from typing import Optional, Union, List, Dict


import matplotlib as mpl





# Set font for charts


plt.rcParams['font.sans-serif'] = ['Arial']  # Use Arial


plt.rcParams['axes.unicode_minus'] = False  # Fix minus sign display





class FeishuNotifier:


    """Feishu bot notification class for sending various messages to Feishu groups"""


    


    def __init__(self, webhook: str = None):


        """


        Initialize Feishu notifier


        Args:


            webhook: Feishu Webhook URL, if not provided will read from FEISHU_WEBHOOK environment variable


        """


        # Set default webhook URL if not provided or found in environment


        default_webhook = "https://www.feishu.cn/flow/api/trigger-webhook/aed5a7c805669fe61a605fe0b93912eb"


        


        # Use the provided webhook, or get from env, or use default


        self.webhook = webhook or os.getenv("FEISHU_WEBHOOK", default_webhook)


        


        # Test the webhook to verify it's valid


        self._test_webhook()


            


    def _test_webhook(self):


        """Test the webhook to verify it's valid"""


        try:


            # Make a minimal request to verify the webhook


            headers = {"Content-Type": "application/json"}


            data = {


                "msg_type": "text",


                "content": {


                    "text": "Webhook test"


                }


            }


            resp = requests.post(self.webhook, json=data, headers=headers, timeout=5)


            resp.raise_for_status()


            


            # If we get here, the webhook is valid


            print(f"Feishu webhook verified: {self.webhook}")


        except Exception as e:


            print(f"Warning: Could not verify Feishu webhook: {e}")


            


    def _setup_chart_font(self, fig):


        """Set up chart font settings"""


        for ax in fig.get_axes():


            # 设置标题字体


            if ax.get_title():


                ax.set_title(ax.get_title(), fontproperties='Arial')


            


            # 设置 x 轴标签字体


            if ax.get_xlabel():


                ax.set_xlabel(ax.get_xlabel(), fontproperties='Arial')


            


            # 设置 y 轴标签字体


            if ax.get_ylabel():


                ax.set_ylabel(ax.get_ylabel(), fontproperties='Arial')


            


            # 设置刻度标签字体


            for label in ax.get_xticklabels() + ax.get_yticklabels():


                label.set_fontproperties('Arial')


            


            # 设置图例字体


            if ax.get_legend():


                for text in ax.get_legend().get_texts():


                    text.set_fontproperties('Arial')





    def send_message(self, title: str, content: str) -> dict:


        """


        发送文本消息


        Args:


            title: 消息标题


            content: 消息内容


        Returns:


            响应JSON


        """


        headers = {"Content-Type": "application/json"}


        data = {


            "msg_type": "post",


            "content": {


                "post": {


                    "zh_cn": {


                        "title": title,


                        "content": [[{


                            "tag": "text",


                            "text": content


                        }]]


                    }


                }


            }


        }


        resp = requests.post(self.webhook, json=data, headers=headers)


        return resp.json()





    def send_image(self, fig: plt.Figure, title: str = "图表") -> dict:


        """


        发送 Matplotlib 图表


        Args:


            fig: Matplotlib 图表对象


            title: 图表标题


        Returns:


            响应JSON


        """


        # 设置中文字体


        self._setup_chart_font(fig)


        


        # 将图表转换为base64


        buf = BytesIO()


        fig.savefig(buf, format='png', bbox_inches='tight', dpi=300)


        buf.seek(0)


        image_base64 = base64.b64encode(buf.getvalue()).decode()


        


        # 构建图片消息


        data = {


            "msg_type": "image",


            "content": {


                "image_key": image_base64


            }


        }


        


        resp = requests.post(self.webhook, json=data)


        return resp.json()


        


    def send_trade_alert(self, symbol: str, action: str, price: float, quantity: int,


                        reason: str = None, timestamp: datetime = None) -> dict:


        """


        发送交易提醒


        Args:


            symbol: 交易标的


            action: 交易动作（买入/卖出）


            price: 交易价格


            quantity: 交易数量


            reason: 交易原因


            timestamp: 交易时间


        """


        timestamp = timestamp or datetime.now()


        title = f"🔔 交易提醒 - {symbol}"


        


        content = f"**交易信息**\n" \


                 f"- 标的: {symbol}\n" \


                 f"- 动作: {action}\n" \


                 f"- 价格: ${price:.2f}\n" \


                 f"- 数量: {quantity}\n" \


                 f"- 时间: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"


                 


        if reason:


            content += f"- 原因: {reason}\n"


            


        return self.send_message(title, content)


        


    def send_risk_alert(self, symbol: str, alert_type: str, message: str,


                       data: Dict = None, timestamp: datetime = None) -> dict:


        """


        发送风险预警


        Args:


            symbol: 交易标的


            alert_type: 预警类型


            message: 预警信息


            data: 额外数据


            timestamp: 预警时间


        """


        timestamp = timestamp or datetime.now()


        title = f"⚠️ 风险预警 - {symbol}"


        


        content = f"**预警信息**\n" \


                 f"- 标的: {symbol}\n" \


                 f"- 类型: {alert_type}\n" \


                 f"- 信息: {message}\n" \


                 f"- 时间: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"


                 


        if data:


            content += "\n**详细数据**\n"


            for key, value in data.items():


                content += f"- {key}: {value}\n"


                


        return self.send_message(title, content)


        


    def send_performance_report(self, total_pnl: float, daily_pnl: float,


                              positions: List[Dict], trades: List[Dict] = None,


                              timestamp: datetime = None) -> dict:


        """


        发送绩效报告


        Args:


            total_pnl: 总盈亏


            daily_pnl: 当日盈亏


            positions: 当前持仓列表


            trades: 当日交易列表


            timestamp: 报告时间


        """


        timestamp = timestamp or datetime.now()


        title = f"📊 绩效报告 - {timestamp.strftime('%Y-%m-%d')}"


        


        # 使用多个content block来改善格式


        contents = []


        


        # 账户概览板块


        contents.append([{


            "tag": "text",


            "text": "💰 账户概览\n"


        }])


        contents.append([{


            "tag": "text",


            "text": f"总盈亏: ${total_pnl:,.2f}\n"


        }])


        contents.append([{


            "tag": "text",


            "text": f"当日盈亏: ${daily_pnl:,.2f}\n"


        }])


        


        # 当前持仓板块


        if positions:


            contents.append([{


                "tag": "text",


                "text": "\n📈 当前持仓\n"


            }])


            for pos in positions:


                contents.append([{


                    "tag": "text",


                    "text": f"{pos['symbol']}: {pos['quantity']}股 @ ${pos['avg_price']:.2f}\n"


                }])


                


        # 当日交易板块


        if trades:


            contents.append([{


                "tag": "text",


                "text": "\n🔄 当日交易\n"


            }])


            for trade in trades:


                contents.append([{


                    "tag": "text",


                    "text": f"{trade['symbol']}: {trade['action']} {trade['quantity']}股 @ ${trade['price']:.2f}\n"


                }])


                


        data = {


            "msg_type": "post",


            "content": {


                "post": {


                    "zh_cn": {


                        "title": title,


                        "content": contents


                    }


                }


            }


        }


        


        headers = {"Content-Type": "application/json"}


        resp = requests.post(self.webhook, json=data, headers=headers)


        return resp.json()





    def send_option_entry_signal(self, 


                           symbol: str,


                           option_type: str,  # 'call' or 'put'


                           strike_price: float,


                           expiry_date: str,


                           current_price: float,


                           implied_volatility: float,


                           pressure_points: Dict[str, float],


                           risk_reward_ratio: float,


                           confidence_score: float,


                           analysis: str) -> dict:


        """


        发送期权入场信号


        


        Args:


            symbol: 标的代码


            option_type: 期权类型 ('call' 或 'put')


            strike_price: 行权价


            expiry_date: 到期日 (YYYY-MM-DD)


            current_price: 当前价格


            implied_volatility: 隐含波动率


            pressure_points: 支撑/阻力位


            risk_reward_ratio: 风险收益比


            confidence_score: 置信度


            analysis: 分析说明


            


        Returns:


            响应JSON


        """


        # 方向表情


        direction_emoji = "🟢" if option_type.lower() == "call" else "🔴"


        


        # 标题


        title = f"{direction_emoji} 期权信号 - {symbol}"


        


        # 支撑位和阻力位


        support = pressure_points.get("support", 0)


        resistance = pressure_points.get("resistance", 0)


        


        # 构建内容


        content = f"**期权类型**: {option_type.upper()}\n" \


                 f"**行权价**: ${strike_price:.2f}\n" \


                 f"**到期日**: {expiry_date}\n" \


                 f"**当前价格**: ${current_price:.2f}\n" \


                 f"**隐含波动率**: {implied_volatility*100:.1f}%\n"


                 


        # 添加压力位信息(如果有)


        if support > 0 or resistance > 0:


            content += "**压力位**:\n"


            if support > 0:


                content += f"- 支撑: ${support:.2f}\n"


            if resistance > 0:


                content += f"- 阻力: ${resistance:.2f}\n"


                


        # 添加风险收益比和置信度


        content += f"**风险收益比**: {risk_reward_ratio:.2f}\n" \


                  f"**置信度**: {confidence_score*100:.1f}%\n"


        


        # 添加分析


        if analysis:


            content += f"\n**分析**:\n{analysis}\n"


        


        # 发送通知


        return self.send_message(title, content)





    def send_market_analysis(self,


                           market_condition: str,  # 'bullish', 'bearish', or 'neutral'


                           vix_level: float,


                           sector_performance: Dict[str, float],


                           key_events: List[Dict],


                           trading_suggestions: List[str]) -> dict:


        """


        发送市场分析报告


        Args:


            market_condition: 市场状况


            vix_level: VIX指数水平


            sector_performance: 各板块表现


            key_events: 关键事件列表


            trading_suggestions: 交易建议列表


        """


        title = f"📊 市场分析报告 - {datetime.now().strftime('%Y-%m-%d')}"


        


        contents = []


        


        # 市场状况


        condition_emoji = {


            'bullish': '🐂',


            'bearish': '🐻',


            'neutral': '⚖️'


        }


        


        contents.append([{


            "tag": "text",


            "text": f"{condition_emoji.get(market_condition, '📊')} 市场状况\n"


        }])


        contents.append([{


            "tag": "text",


            "text": f"市场情绪: {market_condition}\n"


                   f"VIX指数: {vix_level:.2f}\n"


        }])


        


        # 板块表现


        contents.append([{


            "tag": "text",


            "text": f"\n📊 板块表现\n"


        }])


        for sector, perf in sector_performance.items():


            contents.append([{


                "tag": "text",


                "text": f"{sector}: {perf:+.1%}\n"


            }])


        


        # 关键事件


        contents.append([{


            "tag": "text",


            "text": f"\n📅 关键事件\n"


        }])


        for event in key_events:


            contents.append([{


                "tag": "text",


                "text": f"- {event['time']}: {event['description']}\n"


            }])


        


        # 交易建议


        contents.append([{


            "tag": "text",


            "text": f"\n💡 交易建议\n"


        }])


        for suggestion in trading_suggestions:


            contents.append([{


                "tag": "text",


                "text": f"• {suggestion}\n"


            }])


        


        data = {


            "msg_type": "post",


            "content": {


                "post": {


                    "zh_cn": {


                        "title": title,


                        "content": contents


                    }


                }


            }


        }


        


        headers = {"Content-Type": "application/json"}


        resp = requests.post(self.webhook, json=data, headers=headers)


        return resp.json()





    def send_option_chain_analysis(self,


                                 symbol: str,


                                 price: float,


                                 expiry_dates: List[str],


                                 iv_skew: Dict[str, float],


                                 volume_analysis: Dict[str, Dict],


                                 unusual_activity: List[Dict],


                                 recommendations: List[str]) -> dict:


        """


        发送期权链分析


        Args:


            symbol: 标的股票代码


            price: 当前价格


            expiry_dates: 主要到期日列表


            iv_skew: 波动率偏斜数据


            volume_analysis: 成交量分析


            unusual_activity: 异常活动


            recommendations: 建议列表


        """


        title = f"🔍 期权链分析 - {symbol}"


        


        contents = []


        


        # 基本信息


        contents.append([{


            "tag": "text",


            "text": f"📊 基本信息\n"


        }])


        contents.append([{


            "tag": "text",


            "text": f"标的: {symbol}\n"


                   f"当前价格: ${price:.2f}\n"


        }])


        


        # 波动率偏斜


        contents.append([{


            "tag": "text",


            "text": f"\n📈 波动率偏斜\n"


        }])


        for exp, skew in iv_skew.items():


            contents.append([{


                "tag": "text",


                "text": f"{exp}: {skew:+.2f}\n"


            }])


        


        # 成交量分析


        contents.append([{


            "tag": "text",


            "text": f"\n📊 成交量分析\n"


        }])


        for exp, data in volume_analysis.items():


            contents.append([{


                "tag": "text",


                "text": f"{exp}:\n"


                       f"看涨/看跌比率: {data['call_put_ratio']:.2f}\n"


                       f"主力关注度: {data['institutional_interest']:.0%}\n"


            }])


        


        # 异常活动


        if unusual_activity:


            contents.append([{


                "tag": "text",


                "text": f"\n⚠️ 异常活动\n"


            }])


            for activity in unusual_activity:


                contents.append([{


                    "tag": "text",


                    "text": f"- {activity['description']}\n"


                }])


        


        # 建议


        contents.append([{


            "tag": "text",


            "text": f"\n💡 建议\n"


        }])


        for rec in recommendations:


            contents.append([{


                "tag": "text",


                "text": f"• {rec}\n"


            }])


        


        data = {


            "msg_type": "post",


            "content": {


                "post": {


                    "zh_cn": {


                        "title": title,


                        "content": contents


                    }


                }


            }


        }


        


        headers = {"Content-Type": "application/json"}


        resp = requests.post(self.webhook, json=data, headers=headers)


        return resp.json() 