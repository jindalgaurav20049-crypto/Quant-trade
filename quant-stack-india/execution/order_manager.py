"""
Order Manager

Routes orders to the active broker with retry logic and logging.
"""

import os
import logging
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)


class OrderManager:
    """
    Central order management with broker routing and retry logic.
    """
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize order manager.
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.broker = self._initialize_broker()
        self.order_history: List[dict] = []
    
    def _initialize_broker(self):
        """Initialize the active broker based on configuration."""
        broker_name = os.getenv("ACTIVE_BROKER", "zerodha").lower()
        
        if broker_name == "zerodha":
            from .brokers.zerodha_broker import ZerodhaBroker
            return ZerodhaBroker()
        elif broker_name == "angel":
            from .brokers.angel_broker import AngelBroker
            return AngelBroker()
        elif broker_name == "fyers":
            from .brokers.fyers_broker import FyersBroker
            return FyersBroker()
        else:
            logger.error(f"Unknown broker: {broker_name}, defaulting to Zerodha")
            from .brokers.zerodha_broker import ZerodhaBroker
            return ZerodhaBroker()
    
    def place_order(
        self,
        ticker: str,
        qty: int,
        side: str,
        order_type: str = "MARKET",
        product: str = "CNC",
        price: float = 0.0,
        tag: str = "quant-stack"
    ) -> Optional[str]:
        """
        Place an order with retry logic.
        
        Args:
            ticker: Stock symbol
            qty: Quantity
            side: "BUY" or "SELL"
            order_type: "MARKET" or "LIMIT"
            product: "CNC", "MIS", or "NRML"
            price: Limit price
            tag: Order tag
            
        Returns:
            Order ID or None on failure
        """
        for attempt in range(self.max_retries):
            try:
                order_id = self.broker.place_order(
                    ticker=ticker,
                    qty=qty,
                    side=side,
                    order_type=order_type,
                    product=product,
                    price=price,
                    tag=tag
                )
                
                if order_id:
                    # Log successful order
                    self.order_history.append({
                        "order_id": order_id,
                        "ticker": ticker,
                        "qty": qty,
                        "side": side,
                        "status": "PLACED",
                        "attempts": attempt + 1,
                    })
                    return order_id
                
            except Exception as e:
                logger.error(f"Order attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        
        # All retries failed
        logger.error(f"Order failed after {self.max_retries} attempts")
        self.order_history.append({
            "ticker": ticker,
            "qty": qty,
            "side": side,
            "status": "FAILED",
            "attempts": self.max_retries,
        })
        
        return None
    
    def place_orders_batch(
        self,
        orders: List[dict],
        product: str = "CNC"
    ) -> Dict[str, Optional[str]]:
        """
        Place multiple orders.
        
        Args:
            orders: List of order dictionaries
            product: Product type
            
        Returns:
            Dictionary mapping ticker to order ID
        """
        results = {}
        
        for order in orders:
            order_id = self.place_order(
                ticker=order["ticker"],
                qty=order["qty"],
                side=order["side"],
                product=product,
                price=order.get("price", 0.0)
            )
            results[order["ticker"]] = order_id
        
        return results
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if successful
        """
        return self.broker.cancel_order(order_id)
    
    def get_positions(self):
        """Get current positions."""
        return self.broker.get_positions()
    
    def get_holdings(self):
        """Get holdings."""
        return self.broker.get_holdings()
    
    def get_margins(self):
        """Get available margins."""
        return self.broker.get_margins()
    
    def get_order_history(self) -> List[dict]:
        """Get order history."""
        return self.order_history


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test OrderManager ===")
    manager = OrderManager()
    
    order_id = manager.place_order("RELIANCE.NS", 10, "BUY")
    print(f"Order ID: {order_id}")
    
    margins = manager.get_margins()
    print(f"Margins: {margins}")
