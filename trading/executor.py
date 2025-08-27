from typing import Optional
from datetime import datetime
import alpaca_trade_api as tradeapi
from enum import Enum

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class TradingExecutor:
    """
    Trading executor using Alpaca as broker
    """
    def __init__(self,
                 api_key: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 base_url: str = "https://paper-api.alpaca.markets"):
        self.api = tradeapi.REST(
            api_key,
            api_secret,
            base_url,
            api_version='v2'
        )
        
    def execute_trade(self,
                     symbol: str,
                     side: OrderSide,
                     quantity: float,
                     price: Optional[float] = None,
                     order_type: OrderType = OrderType.MARKET,
                     time_in_force: str = 'day',
                     stop_loss: Optional[float] = None,
                     take_profit: Optional[float] = None) -> dict:
        """
        Execute a trade order
        
        Args:
            symbol: Stock symbol
            side: Buy or sell
            quantity: Number of shares/contracts
            price: Limit price (required for limit orders)
            order_type: Market, limit, stop, or stop limit
            time_in_force: day, gtc, opg, cls, ioc, fok
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Order details
        """
        try:
            # Submit the primary order
            order = self.api.submit_order(
                symbol=symbol,
                qty=quantity,
                side=side.value,
                type=order_type.value,
                time_in_force=time_in_force,
                limit_price=price if order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] else None,
                stop_price=price if order_type in [OrderType.STOP, OrderType.STOP_LIMIT] else None
            )
            
            # Set stop loss if specified
            if stop_loss and order.status == 'filled':
                self.api.submit_order(
                    symbol=symbol,
                    qty=quantity,
                    side=OrderSide.SELL.value if side == OrderSide.BUY else OrderSide.BUY.value,
                    type=OrderType.STOP.value,
                    time_in_force=time_in_force,
                    stop_price=stop_loss
                )
                
            # Set take profit if specified
            if take_profit and order.status == 'filled':
                self.api.submit_order(
                    symbol=symbol,
                    qty=quantity,
                    side=OrderSide.SELL.value if side == OrderSide.BUY else OrderSide.BUY.value,
                    type=OrderType.LIMIT.value,
                    time_in_force=time_in_force,
                    limit_price=take_profit
                )
                
            return {
                'order_id': order.id,
                'status': order.status,
                'filled_qty': order.filled_qty,
                'filled_avg_price': order.filled_avg_price
            }
            
        except Exception as e:
            raise Exception(f"Failed to execute trade: {str(e)}")
            
    def get_position(self, symbol: str) -> Optional[dict]:
        """Get current position for a symbol"""
        try:
            position = self.api.get_position(symbol)
            return {
                'symbol': position.symbol,
                'qty': float(position.qty),
                'market_value': float(position.market_value),
                'avg_entry_price': float(position.avg_entry_price),
                'unrealized_pl': float(position.unrealized_pl),
                'current_price': float(position.current_price)
            }
        except:
            return None
            
    def get_account(self) -> dict:
        """Get account information"""
        account = self.api.get_account()
        return {
            'cash': float(account.cash),
            'portfolio_value': float(account.portfolio_value),
            'buying_power': float(account.buying_power),
            'day_trade_count': int(account.daytrade_count)
        } 