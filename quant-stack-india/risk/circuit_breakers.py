"""
NSE Circuit Breaker Rules
==========================
NSE applies two types of circuit limits:

1. Stock-level bands: stocks have ±5%, ±10%, or ±20% price bands
   depending on their category (A/B/T group).
   Orders outside these bands are REJECTED by the exchange.

2. Index-level halt: if Nifty 50 moves ±10% intraday, trading halts for 45 min.
   ±15% → halt for 1 hour 45 min. ±20% → remainder of day halt.

This module pre-validates orders to prevent NSE rejections.
"""

import logging
from typing import Dict, Optional, List
import pandas as pd

logger = logging.getLogger(__name__)

NSE_CIRCUIT_BANDS: Dict[str, float] = {
    "A": 0.20, "B": 0.10, "T": 0.05, "XT": 0.05,
    "Z": 0.05, "BE": 0.05, "default": 0.10
}

INDEX_HALT_LEVELS = [0.10, 0.15, 0.20]

NIFTY50_CATEGORY: Dict[str, str] = {
    t: "A" for t in [
        "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR",
        "BAJFINANCE", "SBIN", "BHARTIARTL", "WIPRO", "HCLTECH", "ASIANPAINT",
        "MARUTI", "TITAN", "SUNPHARMA", "ULTRACEMCO", "NESTLEIND", "AXISBANK",
        "KOTAKBANK", "LT", "POWERGRID", "NTPC", "ONGC", "COALINDIA", "TECHM",
        "PERSISTENT", "MPHASIS", "DIXON", "TATAELXSI", "MAXHEALTH",
        "INDUSINDBK", "BANKBARODA", "PNB",
    ]
}


def get_circuit_band(ticker: str) -> float:
    clean = ticker.replace(".NS", "").replace(".BO", "")
    category = NIFTY50_CATEGORY.get(clean, "default")
    return NSE_CIRCUIT_BANDS.get(category, NSE_CIRCUIT_BANDS["default"])


def check_order_within_band(
    ticker: str,
    order_price: float,
    prev_close: float
) -> tuple:
    """
    Returns (is_valid: bool, reason: str).
    Validates order price is within NSE circuit limits.
    """
    if prev_close <= 0:
        logger.warning(f"No prev_close for {ticker} — skipping circuit check")
        return True, "no_prev_close"
    band = get_circuit_band(ticker)
    upper = prev_close * (1 + band)
    lower = prev_close * (1 - band)
    if order_price > upper:
        return False, f"REJECTED: {ticker} order price ₹{order_price:.2f} > upper band ₹{upper:.2f} (±{band*100:.0f}%)"
    if order_price < lower:
        return False, f"REJECTED: {ticker} order price ₹{order_price:.2f} < lower band ₹{lower:.2f} (±{band*100:.0f}%)"
    return True, "ok"


def check_index_halt(nifty_change_pct: float) -> tuple:
    """
    Returns (trading_halted: bool, reason: str).
    """
    abs_change = abs(nifty_change_pct)
    if abs_change >= 0.20:
        return True, "MARKET HALT: Nifty moved ±20% — trading suspended for remainder of day"
    elif abs_change >= 0.15:
        return True, "MARKET HALT: Nifty moved ±15% — trading halted for 1 hour 45 minutes"
    elif abs_change >= 0.10:
        return True, "MARKET HALT: Nifty moved ±10% — trading halted for 45 minutes"
    return False, "ok"


def validate_order_batch(
    orders: List[dict],
    prev_closes: Dict[str, float],
    nifty_change_pct: float = 0.0
) -> List[dict]:
    """
    Filter a list of order dicts, removing any that would be circuit-rejected.
    orders: list of {'ticker', 'qty', 'side', 'price'} dicts
    Returns filtered list of valid orders.
    """
    halted, halt_reason = check_index_halt(nifty_change_pct)
    if halted:
        logger.error(halt_reason)
        return []

    valid_orders = []
    for order in orders:
        ticker = order.get("ticker", "")
        price = order.get("price", 0.0)
        prev_close = prev_closes.get(ticker.replace(".NS", "").replace(".BO", ""), 0.0)
        if price <= 0:
            valid_orders.append(order)  # market order — let exchange handle it
            continue
        is_valid, reason = check_order_within_band(ticker, price, prev_close)
        if is_valid:
            valid_orders.append(order)
        else:
            logger.warning(reason)
    return valid_orders


def get_circuit_limits(ticker: str, prev_close: float) -> Dict[str, float]:
    """
    Get circuit limits for a stock.
    
    Args:
        ticker: Stock symbol
        prev_close: Previous close price
        
    Returns:
        Dictionary with upper and lower limits
    """
    band = get_circuit_band(ticker)
    
    return {
        'upper': prev_close * (1 + band),
        'lower': prev_close * (1 - band),
        'band': band,
        'band_pct': band * 100,
    }


def is_near_circuit(
    ticker: str,
    current_price: float,
    prev_close: float,
    threshold: float = 0.02
) -> bool:
    """
    Check if a stock is near its circuit limit.
    
    Args:
        ticker: Stock symbol
        current_price: Current price
        prev_close: Previous close price
        threshold: Distance threshold as fraction of band
        
    Returns:
        True if near circuit
    """
    limits = get_circuit_limits(ticker, prev_close)
    
    dist_to_upper = (limits['upper'] - current_price) / prev_close
    dist_to_lower = (current_price - limits['lower']) / prev_close
    
    return dist_to_upper < threshold or dist_to_lower < threshold


if __name__ == "__main__":
    # Test the module
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test get_circuit_band ===")
    for ticker in ["RELIANCE.NS", "TCS.NS", "UNKNOWN.NS"]:
        band = get_circuit_band(ticker)
        print(f"{ticker}: ±{band*100:.0f}%")
    
    print("\n=== Test check_order_within_band ===")
    result, reason = check_order_within_band("RELIANCE.NS", 3000, 2500)
    print(f"Order at 3000, prev_close 2500: {result}, {reason}")
    
    result, reason = check_order_within_band("RELIANCE.NS", 2600, 2500)
    print(f"Order at 2600, prev_close 2500: {result}, {reason}")
    
    print("\n=== Test check_index_halt ===")
    for change in [0.05, 0.12, 0.18, 0.25]:
        halted, reason = check_index_halt(change)
        print(f"Nifty change {change*100:.0f}%: halted={halted}")
    
    print("\n=== Test validate_order_batch ===")
    orders = [
        {"ticker": "RELIANCE.NS", "qty": 10, "side": "BUY", "price": 2600},
        {"ticker": "TCS.NS", "qty": 5, "side": "BUY", "price": 4000},
    ]
    prev_closes = {"RELIANCE": 2500, "TCS": 3500}
    valid = validate_order_batch(orders, prev_closes, nifty_change_pct=0.05)
    print(f"Valid orders: {len(valid)}/{len(orders)}")
