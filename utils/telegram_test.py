import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from data.itch_loader import itch_loader
from utils.telegram_notifier import notifier
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from typing import Dict, Any

def create_market_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Create a market summary from OHLCV data."""
    latest = df.iloc[-1]
    first = df.iloc[0]
    
    # Calculate basic metrics
    price_change = latest['close'] - first['close']
    price_change_pct = (price_change / first['close']) * 100
    
    # Calculate VWAP
    vwap = (df['close'] * df['volume']).sum() / df['volume'].sum()
    
    return {
        'current_price': latest['close'],
        'open_price': first['open'],
        'high': df['high'].max(),
        'low': df['low'].min(),
        'volume': df['volume'].sum(),
        'price_change': price_change,
        'price_change_pct': price_change_pct,
        'vwap': vwap
    }

def generate_test_message() -> bool:
    """Generate and send a test message using sample data."""
    try:
        # Load sample data
        print("Loading sample ITCH data...")
        df = itch_loader.load_mbo_data()
        
        # Create market summary
        summary = create_market_summary(df)
        
        # Format message
        message = (
            "🤖 *System Test Message*\n\n"
            "📊 Market Summary (MSFT)\n"
            f"Current Price: ${summary['current_price']:.2f}\n"
            f"Open: ${summary['open_price']:.2f}\n"
            f"High: ${summary['high']:.2f}\n"
            f"Low: ${summary['low']:.2f}\n"
            f"VWAP: ${summary['vwap']:.2f}\n\n"
            f"Change: {summary['price_change_pct']:+.2f}% "
            f"(${summary['price_change']:+.2f})\n"
            f"Volume: {summary['volume']:,.0f}\n\n"
            "🕒 Generated: "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Create candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close']
        )])
        
        fig.update_layout(
            title="MSFT Price Movement",
            yaxis_title="Price ($)",
            template="plotly_dark"
        )
        
        # Save chart
        chart_path = "temp_charts/test_chart.png"
        Path("temp_charts").mkdir(exist_ok=True)
        fig.write_image(chart_path)
        
        # Send message and chart
        print("Sending test message...")
        msg_result = notifier.send_message(message)
        
        if msg_result.get("error"):
            print(f"Error sending message: {msg_result['error']}")
            return False
            
        print("Sending test chart...")
        chart_result = notifier.send_photo(chart_path)
        
        if chart_result.get("error"):
            print(f"Error sending chart: {chart_result['error']}")
            return False
        
        print("✅ Test message sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

if __name__ == "__main__":
    success = generate_test_message()
    print(f"\nTest {'succeeded' if success else 'failed'}") 