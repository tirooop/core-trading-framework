"""
Notification utilities for trading signals
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

class Notifier:
    """Simple notification handler"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def send_alert(self, title: str, message: Any) -> None:
        """
        Send an alert
        
        Args:
            title: Alert title
            message: Alert message (can be any type)
        """
        try:
            # Log the alert
            self.logger.info(f"{title}: {message}")
            
            # TODO: Add more notification channels (Telegram, Email, etc.)
            
        except Exception as e:
            self.logger.error(f"Error sending alert: {str(e)}")
    
    def send_trade_signal(self, signal: Dict) -> None:
        """
        Send a trade signal notification
        
        Args:
            signal: Dictionary containing signal information
        """
        try:
            title = f"Trade Signal: {signal['symbol']}"
            message = (
                f"Direction: {signal['direction']}\n"
                f"Strength: {signal['strength']:.2f}\n"
                f"Price: {signal['current_price']:.2f}\n"
                f"Time: {signal['timestamp']}"
            )
            
            self.send_alert(title, message)
            
        except Exception as e:
            self.logger.error(f"Error sending trade signal: {str(e)}") 