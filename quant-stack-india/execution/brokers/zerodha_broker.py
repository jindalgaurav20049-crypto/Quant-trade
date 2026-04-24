"""
Zerodha KiteConnect Broker Wrapper
===================================
Handles all interactions with Zerodha via pykiteconnect.

IMPORTANT: Zerodha requires a fresh access token EVERY DAY.
Token refresh is handled by automation/token_refresh.py which
runs at 08:00 IST using pyotp for TOTP-based 2FA.

Paper trading mode: Since Zerodha has no native paper mode,
paper trades are simulated locally — orders are logged but
NOT sent to the exchange. Set TRADING_MODE=paper in .env.
"""

import os
import json
import logging
import time
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import pytz

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

TOKEN_FILE = Path(".zerodha_token.json")


class ZerodhaBroker:
    def __init__(self):
        self.api_key = os.getenv("ZERODHA_API_KEY", "")
        self.api_secret = os.getenv("ZERODHA_API_SECRET", "")
        self.trading_mode = os.getenv("TRADING_MODE", "paper").lower()
        self.kite = None
        self._paper_orders: List[dict] = []
        self._paper_positions: Dict[str, dict] = {}
        self._paper_cash: float = 1_000_000.0  # ₹10L paper capital

        if not self.api_key or self.api_key == "your_api_key_here":
            logger.warning("ZERODHA_API_KEY not set — running in simulation mode")
            self.trading_mode = "paper"
        else:
            try:
                from kiteconnect import KiteConnect
                self.kite = KiteConnect(api_key=self.api_key)
                self._load_access_token()
            except ImportError:
                logger.error("kiteconnect not installed. Run: pip install kiteconnect==5.0.1")
                self.trading_mode = "paper"
            except Exception as e:
                logger.warning(f"KiteConnect init failed: {e} — falling back to paper mode")
                self.trading_mode = "paper"

    def _load_access_token(self):
        """Load saved access token from disk. Token valid for one calendar day."""
        if not TOKEN_FILE.exists():
            logger.warning("No Zerodha access token found. Run: python automation/token_refresh.py")
            return
        try:
            with open(TOKEN_FILE) as f:
                data = json.load(f)
            token_date = data.get("date", "")
            today = date.today().isoformat()
            if token_date != today:
                logger.warning(f"Token is from {token_date}, today is {today}. Run token_refresh.py")
                return
            if self.kite:
                self.kite.set_access_token(data["access_token"])
                logger.info("Zerodha access token loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load access token: {e}")

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
        ticker: NSE symbol without .NS suffix (e.g. "RELIANCE" not "RELIANCE.NS")
        side: "BUY" or "SELL"
        product: "CNC" (delivery), "MIS" (intraday), "NRML" (F&O)
        Returns order_id string or None on failure.
        """
        # Strip .NS/.BO suffix if present
        clean_ticker = ticker.replace(".NS", "").replace(".BO", "")

        if qty <= 0:
            logger.warning(f"Skipping order for {clean_ticker}: qty={qty} (must be > 0)")
            return None

        if self.trading_mode == "paper":
            order_id = f"PAPER_{clean_ticker}_{side}_{int(time.time())}"
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
            logger.info(f"[PAPER] {side} {qty} {clean_ticker} ({product}) — order_id: {order_id}")
            return order_id

        # Live order
        try:
            from kiteconnect import KiteConnect
            params = {
                "tradingsymbol": clean_ticker,
                "exchange": "NSE",
                "transaction_type": side,
                "quantity": qty,
                "order_type": order_type,
                "product": product,
                "tag": tag,
            }
            if order_type == "LIMIT" and price > 0:
                params["price"] = price
            
            order_id = self.kite.place_order(variety="regular", **params)
            logger.info(f"[LIVE] {side} {qty} {clean_ticker} — order_id: {order_id}")
            return str(order_id)
        except Exception as e:
            logger.error(f"Order placement failed for {clean_ticker}: {e}")
            return None

    def get_positions(self) -> pd.DataFrame:
        """Return current open positions as DataFrame."""
        if self.trading_mode == "paper":
            return pd.DataFrame(self._paper_positions.values())
        try:
            pos = self.kite.positions()
            all_pos = pos.get("net", []) + pos.get("day", [])
            return pd.DataFrame(all_pos)
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            return pd.DataFrame()

    def get_holdings(self) -> pd.DataFrame:
        """Return delivery holdings (CNC)."""
        if self.trading_mode == "paper":
            return pd.DataFrame()
        try:
            return pd.DataFrame(self.kite.holdings())
        except Exception as e:
            logger.error(f"Failed to fetch holdings: {e}")
            return pd.DataFrame()

    def get_margins(self) -> dict:
        """Return available margin/cash."""
        if self.trading_mode == "paper":
            return {"available": {"live_balance": self._paper_cash}, "mode": "paper"}
        try:
            return self.kite.margins()
        except Exception as e:
            logger.error(f"Failed to fetch margins: {e}")
            return {"available": {"live_balance": 0}, "error": str(e)}

    def cancel_order(self, order_id: str) -> bool:
        if self.trading_mode == "paper":
            logger.info(f"[PAPER] Cancelled order {order_id}")
            return True
        try:
            self.kite.cancel_order(variety="regular", order_id=order_id)
            return True
        except Exception as e:
            logger.error(f"Cancel order failed: {e}")
            return False

    def get_order_history(self, order_id: str) -> List[dict]:
        """Get order history."""
        if self.trading_mode == "paper":
            return [o for o in self._paper_orders if o["order_id"] == order_id]
        try:
            return self.kite.order_history(order_id)
        except Exception as e:
            logger.error(f"Failed to get order history: {e}")
            return []

    def get_ltp(self, ticker: str) -> Optional[float]:
        """Get last traded price."""
        clean_ticker = ticker.replace(".NS", "").replace(".BO", ""

)
        if self.trading_mode == "paper":
            return None
        try:
            ltp_data = self.kite.ltp(f"NSE:{clean_ticker}")
            return ltp_data.get(f"NSE:{clean_ticker}", {}).get("last_price")
        except Exception as e:
            logger.error(f"Failed to get LTP for {clean_ticker}: {e}")
            return None


if __name__ == "__main__":
    # Test the module
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test ZerodhaBroker (Paper Mode) ===")
    broker = ZerodhaBroker()
    
    print(f"\nTrading mode: {broker.trading_mode}")
    
    print("\n=== Test place_order ===")
    order_id = broker.place_order("RELIANCE.NS", 10, "BUY", product="CNC")
    print(f"Order ID: {order_id}")
    
    print("\n=== Test get_positions ===")
    positions = broker.get_positions()
    print(f"Positions: {positions}")
    
    print("\n=== Test get_margins ===")
    margins = broker.get_margins()
    print(f"Margins: {margins}")
