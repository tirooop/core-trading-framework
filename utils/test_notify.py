"""
测试统一通知功能
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 直接设置环境变量
os.environ["FEISHU_WEBHOOK"] = "https://www.feishu.cn/flow/api/trigger-webhook/aed5a7c805669fe61a605fe0b93912eb"

import numpy as np
import matplotlib.pyplot as plt
from utils.unified_notifier import UnifiedNotifier

def test_notifications():
    # Create notifier with direct token/webhook values
    notifier = UnifiedNotifier(
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        feishu_webhook=os.getenv("FEISHU_WEBHOOK")
    )
    
    # Test basic message
    print("Testing basic message...")
    result = notifier.send_message("🔔 Test notification from RL Option Trader!")
    print(f"Basic message result: {result}")
    
    # Test option entry signal
    print("\nTesting option entry signal...")
    result = notifier.send_option_entry_signal(
        symbol="AAPL",
        strike=150.0,
        expiry="2024-06-21",
        position="LONG CALL",
        entry_price=5.20,
        stop_loss=4.50,
        take_profit=7.80
    )
    print(f"Option entry signal result: {result}")
    
    # Test market analysis
    print("\nTesting market analysis...")
    result = notifier.send_market_analysis(
        symbol="AAPL",
        trend="BULLISH",
        volatility="MODERATE",
        sentiment="POSITIVE",
        support=145.0,
        resistance=155.0
    )
    print(f"Market analysis result: {result}")
    
    # Test training update
    print("\nTesting training update...")
    result = notifier.send_training_update(
        episode=100,
        reward=156.78,
        metrics={
            "avg_reward": 145.23,
            "win_rate": 0.68,
            "sharpe_ratio": 1.45
        }
    )
    print(f"Training update result: {result}")

if __name__ == "__main__":
    print("开始测试统一通知功能...\n")
    
    # 检查环境变量
    if not os.getenv("FEISHU_WEBHOOK") and not os.getenv("TELEGRAM_BOT_TOKEN"):
        print("⚠️ 警告: 未设置任何通知渠道的环境变量!")
        print("请设置以下环境变量之一或两者都设置:")
        print("- FEISHU_WEBHOOK")
        print("- TELEGRAM_BOT_TOKEN")
        exit(1)
    
    try:
        test_notifications()
        print("\n✅ 所有测试完成!")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {str(e)}") 