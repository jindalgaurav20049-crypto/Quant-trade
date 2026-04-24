"""
Angel One SmartAPI Broker Wrapper

Fallback broker implementation using Angel One SmartAPI.
"""

import os
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import pytz

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")


class AngelBroker:
    """
    Angel One SmartAPI broker wrapper.
    """
    
    def __init__(self):
        self.api_key = os.getenv("ANGEL_API_KEY", "")
        self.client_id = os.getenv("ANGEL_CLIENT_ID", "")
        self.password = os.getenv("ANGEL_PASSWORD", "")
        self.totp_secret = os.getenv("ANGEL_TOTP_SECRET", "")
        self.trading_mode = os.getenv("TRADING_MODE", "paper").lower()
        
        self.smart_api = None
        self._paper_orders: List[dict] = []
        self._paper_positions: Dict[str, dict] = {}
        self._paper_cash: float = 1_000_000.0
        
        if not self.api_key or self.api_key == "your_api_key_here":
            logger.warning("ANGEL_API_KEY not set — running in simulation mode")
            self.trading_mode = "paper"
        else:
            try:
                from smartapi import SmartConnect
                self.smart_api = SmartConnect(api_key=self.api_key)
                # Login would happen here in production
                logger.info("Angel SmartAPI initialized")
            except ImportError:
                logger.error("smartapi not installed. Run: pip install smartapi-python==1.3.9")
                self.trading_mode = "paper"
            except Exception as e:
                logger.warning(f"SmartAPI init failed: {e} — falling back to paper mode")
                self.trading_mode = "paper"
    
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
        Place buy/sell order.
        
        Args:
            ticker: Stock symbol
            qty: Quantity
            side: "BUY" or "SELL"
            order_type: "MARKET" or "LIMIT"
            product: "CNC", "MIS", or "NRML"
            price: Limit price (for LIMIT orders)
            tag: Order tag
            
        Returns:
            Order ID or None on failure
        """
        clean_ticker = ticker.replace(".NS", "").replace(".BO", "")
        
        if qty <= 0:
            logger.warning(f"Skipping order for {clean_ticker}: qty={qty}")
            return None
        
        if self.trading_mode == "paper":
            order_id = f"ANGEL_PAPER_{clean_ticker}_{side}_{int(time.time())}"
            order = {
                "order_id": order_id,
                "ticker": clean_ticker,
                "qty": qty,
                "side": side,
                "order_type": order_type,
                "product": product,
                "timestamp": datetime.now(IST).isoformat(),
                "status": "COMPLETE",
                "mode": "paper"
            }
            self._paper_orders.append(order)
            logger.info(f"[ANGEL PAPER] {side} {qty} {clean_ticker}")
            return order_id
        
        # Live order
        try:
            # Map product types
            product_type = "DELIVERY" if product == "CNC" else "INTRADAY"
            
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": clean_ticker,
                "symboltoken": "",  # Would need to fetch token
                "transactiontype": side,
                "exchange": "NSE",
                "ordertype": order_type,
                "producttype": product_type,
                "duration": "DAY",
                "quantity": str(qty),
            }
            
            if order_type == "LIMIT":
                order_params["price"] = str(price)
            
            response = self.smart_api.placeOrder(order_params)
            order_id = response.get("orderid", "")
            logger.info(f"[ANGEL LIVE] {side} {qty} {clean_ticker} — order_id: {order_id}")
            return order_id
            
        except Exception as e:
            logger.error(f"Angel order failed for {clean_ticker}: {e}")
            return None
    
    def get_positions(self) -> pd.DataFrame:
        """Get current positions."""
        if self.trading_mode == "paper":
            return pd.DataFrame(self._paper_positions.values())
        
        try:
            positions = self.smart_api.position()
            return pd.DataFrame(positions.get("data", []))
        except Exception as e:
            logger.error(f"Failed to fetch Angel positions: {e}")
            return pd.DataFrame()
    
    def get_holdings(self) -> pd.DataFrame:
        """Get holdings."""
        if self.trading_mode == "paper":
            return pd.DataFrame()
        
        try:
            holdings = self.smart_api.holding()
            return pd.DataFrame(holdings.get("data", []))
        except Exception as e:
            logger.error(f"Failed to fetch Angel holdings: {e}")
            return pd.DataFrame()
    
    def get_margins(self) -> dict:
        """Get available margins."""
        if self.trading_mode == "paper":
            return {"available": {"live_balance": self._paper_cash}, "mode": "paper"}
        
        try:
            funds = self.smart_api.rmsLimit()
            return funds.get("data", {})
        except Exception as e:
            logger.error(f"Failed to fetch Angel margins: {e}")
            return {"available": {"live_balance": 0}, "error": str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if self.trading_mode == "paper":
            logger.info(f"[ANGEL PAPER] Cancelled order {order_id}")
            return True
        
        try:
            self.smart_api.cancelOrder(order_id, "NORMAL")
            return True
        except Exception as e:
            logger.error(f"Angel cancel order failed: {e}")
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test AngelBroker (Paper Mode) ===")
    broker = AngelBroker()
    print(f"Trading mode: {broker.trading_mode}")
    
    order_id = broker.place_order("RELIANCE.NS", 10, "BUY")
    print(f"Order ID: {order_id}")
