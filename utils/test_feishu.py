"""
飞书推送测试脚本

使用方法：
1. 设置环境变量 FEISHU_WEBHOOK，值为你的飞书机器人 Webhook URL
   - Windows: set FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
   - Linux/Mac: export FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
   
2. 运行测试脚本：
   python utils/test_feishu.py

注意：
- 请确保你已经在飞书开放平台创建了自定义机器人
- Webhook URL 可以在机器人设置页面获取
- 建议将 Webhook URL 保存在环境变量中，而不是硬编码在代码里
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from feishu_notifier import FeishuNotifier

# 初始化通知器（使用固定的webhook URL进行测试）
FEISHU_WEBHOOK = "https://www.feishu.cn/flow/api/trigger-webhook/aed5a7c805669fe61a605fe0b93912eb"
notifier = FeishuNotifier(webhook=FEISHU_WEBHOOK)

def test_basic_features():
    """测试基础消息功能"""
    print("\n=== 测试基础消息功能 ===")
    
    # 1. 测试文本消息
    print("\n1. 测试文本消息...")
    resp = notifier.send_message(
        title="测试消息",
        content="这是一条测试消息，用于验证飞书机器人功能是否正常。"
    )
    print(f"文本消息响应: {resp}")

    # 2. 测试图表消息
    print("\n2. 测试图表消息...")
    x = np.linspace(0, 10, 100)
    y = np.sin(x)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x, y, 'b-', label='Sine Wave')
    ax.set_title('测试图表')
    ax.set_xlabel('X 轴')
    ax.set_ylabel('Y 轴')
    ax.grid(True)
    ax.legend()
    resp = notifier.send_image(fig, title="测试图表")
    print(f"图表消息响应: {resp}")
    plt.close()

def test_trading_features():
    """测试交易相关功能"""
    print("\n=== 测试交易相关功能 ===")
    
    # 1. 测试期权入场信号
    print("\n1. 测试期权入场信号...")
    entry_response = notifier.send_option_entry_signal(
        symbol="AAPL",
        option_type="call",
        strike_price=180.0,
        expiry_date="2024-05-17",
        current_price=175.84,
        implied_volatility=0.28,
        pressure_points={
            "support": 178.50,
            "resistance": 185.00,
            "stop_loss": 174.50
        },
        risk_reward_ratio=2.8,
        confidence_score=0.82,
        analysis="MACD金叉 + EMA突破，且看涨期权链隐含波动率整体抬升。"
                "机构大量买入180C，成交量显著放大。"
    )
    print(f"入场信号响应: {entry_response}")
    
    # 2. 测试市场分析
    print("\n2. 测试市场分析...")
    market_response = notifier.send_market_analysis(
        market_condition="bullish",
        vix_level=13.5,
        sector_performance={
            "科技": +1.2,
            "半导体": +2.8,
            "金融": -0.5,
            "能源": +0.3
        },
        key_events=[
            {
                "time": "20:00",
                "description": "美联储FOMC会议纪要",
                "impact": "高"
            },
            {
                "time": "22:30",
                "description": "原油库存数据",
                "impact": "中"
            }
        ],
        trading_suggestions=[
            "建议逢低布局高beta科技股",
            "半导体板块可能出现突破机会",
            "关注美联储纪要对金融股影响"
        ]
    )
    print(f"市场分析响应: {market_response}")
    
    # 3. 测试期权链分析
    print("\n3. 测试期权链分析...")
    chain_response = notifier.send_option_chain_analysis(
        symbol="TSLA",
        price=238.45,
        expiry_dates=["2024-04-19", "2024-05-17", "2024-06-21"],
        iv_skew={
            "2024-04-19": -0.15,
            "2024-05-17": -0.08,
            "2024-06-21": -0.05
        },
        volume_analysis={
            "2024-04-19": {
                "call_put_ratio": 1.56,
                "institutional_interest": 0.75
            },
            "2024-05-17": {
                "call_put_ratio": 1.82,
                "institutional_interest": 0.85
            },
            "2024-06-21": {
                "call_put_ratio": 1.65,
                "institutional_interest": 0.80
            }
        },
        unusual_activity=[
            {
                "strike": 250,
                "type": "call",
                "volume": 10000,
                "description": "大资金买入250C，成交量超过均值300%"
            }
        ],
        recommendations=[
            "看涨偏向明显，机构大量买入看涨期权",
            "短期波动率预期较低，可考虑卖出跨式策略",
            "重点关注250C的大单建仓"
        ]
    )
    print(f"期权链分析响应: {chain_response}")

if __name__ == "__main__":
    print("开始飞书推送功能测试...\n")
    print(f"使用Webhook URL: {FEISHU_WEBHOOK}")
    
    try:
        test_basic_features()
        test_trading_features()
        print("\n✅ 所有测试完成!")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {str(e)}") 