"""
Fyers API v3 Broker Wrapper

Fallback broker implementation using Fyers API v3.
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


class FyersBroker:
    """
    Fyers API v3 broker wrapper.
    """
    
    def __init__(self):
        self.client_id = os.getenv("FYERS_CLIENT_ID", "")
        self.secret_key = os.getenv("FYERS_SECRET_KEY", "")
        self.redirect_uri = os.getenv("FYERS_REDIRECT_URI", "https://127.0.0.1")
        self.trading_mode = os.getenv("TRADING_MODE", "paper").lower()
        
        self.fyers = None
        self._paper_orders: List[dict] = []
        self._paper_positions: Dict[str, dict] = {}
        self._paper_cash: float = 1_000_000.0
        
        if not self.client_id or self.client_id == "your_client_id_here":
            logger.warning("FYERS_CLIENT_ID not set — running in simulation mode")
            self.trading_mode = "paper"
        else:
            try:
                from fyers_apiv3 import fyersModel
                self.fyers_model = fyersModel
                # Fyers requires access token generation first
                logger.info("Fyers API initialized (token required)")
            except ImportError:
                logger.error("fyers_apiv3 not installed. Run: pip install fyers-apiv3==3.1.3")
                self.trading_mode = "paper"
            except Exception as e:
                logger.warning(f"Fyers init failed: {e} — falling back to paper mode")
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
            price: Limit price
            tag: Order tag
            
        Returns:
            Order ID or None on failure
        """
        clean_ticker = ticker.replace(".NS", "").replace(".BO", "")
        
        if qty <= 0:
            logger.warning(f"Skipping order for {clean_ticker}: qty={qty}")
            return None
        
        if self.trading_mode == "paper":
            order_id = f"FYERS_PAPER_{clean_ticker}_{side}_{int(time.time())}"
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
            logger.info(f"[FYERS PAPER] {side} {qty} {clean_ticker}")
            return order_id
        
        # Live order
        try:
            # Map product types
            product_type = "CNC" if product == "CNC" else "INTRADAY"
            
            order_data = {
                "symbol": f"NSE:{clean_ticker}-EQ",
                "qty": qty,
                "type": 2 if order_type == "MARKET" else 1,  # 2=Market, 1=Limit
                "side": 1 if side == "BUY" else -1,
                "productType": product_type,
                "limitPrice": price if order_type == "LIMIT" else 0,
                "stopPrice": 0,
                "validity": "DAY",
                "disclosedQty": 0,
                "offlineOrder": False,
                "stopLoss": 0,
                "takeProfit": 0,
            }
            
            response = self.fyers.place_order(order_data)
            order_id = response.get("id", "")
            logger.info(f"[FYERS LIVE] {side} {qty} {clean_ticker} — order_id: {order_id}")
            return order_id
            
        except Exception as e:
            logger.error(f"Fyers order failed for {clean_ticker}: {e}")
            return None
    
    def get_positions(self) -> pd.DataFrame:
        """Get current positions."""
        if self.trading_mode == "paper":
            return pd.DataFrame(self._paper_positions.values())
        
        try:
            positions = self.fyers.positions()
            return pd.DataFrame(positions.get("netPositions", []))
        except Exception as e:
            logger.error(f"Failed to fetch Fyers positions: {e}")
            return pd.DataFrame()
    
    def get_holdings(self) -> pd.DataFrame:
        """Get holdings."""
        if self.trading_mode == "paper":
            return pd.DataFrame()
        
        try:
            holdings = self.fyers.holdings()
            return pd.DataFrame(holdings.get("holdings", []))
        except Exception as e:
            logger.error(f"Failed to fetch Fyers holdings: {e}")
            return pd.DataFrame()
    
    def get_margins(self) -> dict:
        """Get available margins."""
        if self.trading_mode == "paper":
            return {"available": {"live_balance": self._paper_cash}, "mode": "paper"}
        
        try:
            funds = self.fyers.funds()
            return funds
        except Exception as e:
            logger.error(f"Failed to fetch Fyers margins: {e}")
            return {"available": {"live_balance": 0}, "error": str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if self.trading_mode == "paper":
            logger.info(f"[FYERS PAPER] Cancelled order {order_id}")
            return True
        
        try:
            self.fyers.cancel_order(order_id)
            return True
        except Exception as e:
            logger.error(f"Fyers cancel order failed: {e}")
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test FyersBroker (Paper Mode) ===")
    broker = FyersBroker()
    print(f"Trading mode: {broker.trading_mode}")
    
    order_id = broker.place_order("RELIANCE.NS", 10, "BUY")
    print(f"Order ID: {order_id}")
