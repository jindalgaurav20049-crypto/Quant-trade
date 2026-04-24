"""
Position Sizer — Indian Markets
================================
All position sizes are INTEGER quantities (NSE does not allow fractional shares).
Supports: Kelly criterion, fixed fractional, volatility-scaled sizing.
Integrates with volatility_targeting.py for vol-scaled sizing.
F&O lot sizes enforced when product_type = NRML.
"""

import logging
import math
from typing import Dict, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

NSE_LOT_SIZES: Dict[str, int] = {
    "NIFTY": 75,
    "BANKNIFTY": 30,
    "FINNIFTY": 65,
    "MIDCPNIFTY": 75,
    "SENSEX": 20,
    "RELIANCE": 250,
    "TCS": 150,
    "HDFCBANK": 550,
    "ICICIBANK": 1375,
    "INFY": 300,
    "SBIN": 1500,
}


def round_to_lot_size(qty: int, ticker: str, product: str = "CNC") -> int:
    """Round qty to nearest valid lot size for F&O. For CNC/MIS, minimum is 1."""
    clean = ticker.replace(".NS", "").replace(".BO", "")
    if product == "NRML" and clean in NSE_LOT_SIZES:
        lot = NSE_LOT_SIZES[clean]
        return max(lot, round(qty / lot) * lot)
    return max(1, int(round(qty)))


def kelly_size(
    win_rate: float, avg_win: float, avg_loss: float, kelly_fraction: float = 0.25
) -> float:
    """Kelly criterion. Returns fraction of capital to allocate."""
    if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
        return 0.01
    lose_rate = 1.0 - win_rate
    kelly = (win_rate / avg_loss) - (lose_rate / avg_win)
    return float(np.clip(kelly * kelly_fraction, 0.001, 0.25))


def vol_scaled_qty(
    portfolio_value: float,
    ticker_price: float,
    ticker_vol: float,
    vol_target: float = 0.15,
    ticker: str = "",
    product: str = "CNC",
) -> int:
    """
    Size position so its vol contribution = vol_target / n_positions.
    Assumes single asset for simplicity — in a portfolio, divide vol_target by n.
    """
    if ticker_vol <= 0 or ticker_price <= 0:
        return 0
    notional = (portfolio_value * vol_target) / (ticker_vol * math.sqrt(252))
    raw_qty = notional / ticker_price
    return round_to_lot_size(int(round(raw_qty)), ticker, product)


def fixed_fractional_qty(
    portfolio_value: float,
    ticker_price: float,
    fraction: float = 0.05,
    ticker: str = "",
    product: str = "CNC",
) -> int:
    """Allocate fixed fraction of portfolio. Always round to int."""
    if ticker_price <= 0:
        return 0
    notional = portfolio_value * fraction
    raw_qty = notional / ticker_price
    return round_to_lot_size(int(round(raw_qty)), ticker, product)


def risk_based_qty(
    portfolio_value: float,
    ticker_price: float,
    stop_loss_pct: float,
    risk_per_trade_pct: float = 0.01,
    ticker: str = "",
    product: str = "CNC",
) -> int:
    """
    Size position based on stop loss distance.
    
    Args:
        portfolio_value: Total portfolio value
        ticker_price: Current price
        stop_loss_pct: Stop loss percentage from entry
        risk_per_trade_pct: Risk per trade as % of portfolio
        ticker: Ticker symbol
        product: Product type
        
    Returns:
        Quantity to trade
    """
    if stop_loss_pct <= 0 or ticker_price <= 0:
        return 0
    
    risk_amount = portfolio_value * risk_per_trade_pct
    risk_per_share = ticker_price * stop_loss_pct
    
    if risk_per_share <= 0:
        return 0
    
    raw_qty = risk_amount / risk_per_share
    return round_to_lot_size(int(round(raw_qty)), ticker, product)


def equal_weight_qty(
    portfolio_value: float,
    ticker_price: float,
    n_positions: int,
    ticker: str = "",
    product: str = "CNC",
) -> int:
    """
    Equal weight position sizing.
    
    Args:
        portfolio_value: Total portfolio value
        ticker_price: Current price
        n_positions: Number of positions
        ticker: Ticker symbol
        product: Product type
        
    Returns:
        Quantity to trade
    """
    if n_positions <= 0 or ticker_price <= 0:
        return 0
    
    allocation = portfolio_value / n_positions
    raw_qty = allocation / ticker_price
    return round_to_lot_size(int(round(raw_qty)), ticker, product)


if __name__ == "__main__":
    # Test the module
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test round_to_lot_size ===")
    print(f"RELIANCE CNC qty 105: {round_to_lot_size(105, 'RELIANCE.NS', 'CNC')}")
    print(f"RELIANCE NRML qty 105: {round_to_lot_size(105, 'RELIANCE.NS', 'NRML')}")
    print(f"NIFTY NRML qty 80: {round_to_lot_size(80, 'NIFTY', 'NRML')}")
    
    print("\n=== Test kelly_size ===")
    kelly = kelly_size(win_rate=0.55, avg_win=0.05, avg_loss=0.03)
    print(f"Kelly fraction: {kelly:.4f}")
    
    print("\n=== Test vol_scaled_qty ===")
    qty = vol_scaled_qty(
        portfolio_value=1000000,
        ticker_price=2500,
        ticker_vol=0.25,
        vol_target=0.15
    )
    print(f"Vol-scaled qty: {qty}")
    
    print("\n=== Test fixed_fractional_qty ===")
    qty = fixed_fractional_qty(
        portfolio_value=1000000,
        ticker_price=2500,
        fraction=0.05
    )
    print(f"Fixed fractional qty: {qty}")
    
    print("\n=== Test risk_based_qty ===")
    qty = risk_based_qty(
        portfolio_value=1000000,
        ticker_price=2500,
        stop_loss_pct=0.05,
        risk_per_trade_pct=0.01
    )
    print(f"Risk-based qty: {qty}")
