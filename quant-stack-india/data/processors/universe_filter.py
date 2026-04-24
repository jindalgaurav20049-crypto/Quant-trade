"""
Universe filtering for Indian stocks.

Filters stocks by liquidity, circuit status, and F&O eligibility.
"""

import logging
from typing import List, Dict, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# F&O eligible stocks (major ones - not exhaustive)
FO_ELIGIBLE_STOCKS = {
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR",
    "BAJFINANCE", "SBIN", "BHARTIARTL", "WIPRO", "HCLTECH", "ASIANPAINT",
    "MARUTI", "TITAN", "SUNPHARMA", "ULTRACEMCO", "NESTLEIND", "AXISBANK",
    "KOTAKBANK", "LT", "POWERGRID", "NTPC", "ONGC", "COALINDIA", "TECHM",
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "BAJAJ-AUTO", "BAJAJFINSV",
    "BPCL", "BRITANNIA", "CIPLA", "DIVISLAB", "DRREDDY", "EICHERMOT",
    "GRASIM", "HEROMOTOCO", "HINDALCO", "INDUSINDBK", "ITC", "JSWSTEEL",
    "M&M", "SHREECEM", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "UPL",
    "VEDL", "ABBOTINDIA", "AMBUJACEM", "AUROPHARMA", "BAJAJHLDNG",
    "BALKRISIND", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BERGEPAINT",
    "BIOCON", "BOSCHLTD", "CADILAHC", "COLPAL", "CONCOR", "COROMANDEL",
    "CUMMINSIND", "DABUR", "DEEPAKNTR", "DLF", "ESCORTS", "GAIL",
    "GLAND", "GODREJCP", "GODREJPROP", "HAL", "HAVELLS", "HDFCAMC",
    "HDFCLIFE", "HONAUT", "ICICIGI", "ICICIPRULI", "INDIGO", "NAUKRI",
    "JINDALSTEL", "JUBLFOOD", "LALPATHLAB", "LICHSGFIN", "LTIM",
    "LUPIN", "MANKIND", "MARICO", "MCDOWELL-N", "METROPOLIS", "MFSL",
    "MGL", "MOTHERSON", "MPHASIS", "MUTHOOTFIN", "PAGEIND", "PEL",
    "PERSISTENT", "PETRONET", "PIDILITIND", "PIIND", "POLYCAB", "PVRINOX",
    "RAMCOCEM", "SAIL", "SBICARD", "SBILIFE", "SHRIRAMFIN", "SRF",
    "STARHEALTH", "SUNTV", "SYNGENE", "TATACHEM", "TATACOMM", "TATAPOWER",
    "TATASTEEL", "TORNTPHARM", "TORNTPOWER", "TRENT", "TVSMOTOR",
    "UNITDSPR", "VBL", "VEDL", "WHIRLPOOL", "YESBANK", "ZEEL",
}

# NSE circuit bands by category
CIRCUIT_BANDS = {
    "A": 0.20,  # ±20%
    "B": 0.10,  # ±10%
    "T": 0.05,  # ±5%
    "default": 0.10
}

# Stock categories (simplified)
STOCK_CATEGORIES = {
    "A": [
        "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR",
        "BAJFINANCE", "SBIN", "BHARTIARTL", "WIPRO", "HCLTECH", "ASIANPAINT",
        "MARUTI", "TITAN", "SUNPHARMA", "ULTRACEMCO", "NESTLEIND", "AXISBANK",
        "KOTAKBANK", "LT", "POWERGRID", "NTPC", "ONGC", "COALINDIA", "TECHM",
        "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "BAJAJ-AUTO", "BAJAJFINSV",
        "BPCL", "BRITANNIA", "CIPLA", "DIVISLAB", "DRREDDY", "EICHERMOT",
        "GRASIM", "HEROMOTOCO", "HINDALCO", "INDUSINDBK", "ITC", "JSWSTEEL",
        "M&M", "SHREECEM", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "UPL",
    ],
    "B": [],  # Mid-caps (would need to be populated)
    "T": [],  # Trade-to-trade (would need to be populated)
}


def filter_liquid_stocks(
    price_dict: Dict[str, pd.DataFrame],
    min_avg_volume: int = 100000,
    min_avg_value: float = 50000000,  # ₹5 Cr
    lookback_days: int = 20
) -> List[str]:
    """
    Filter stocks by liquidity criteria.
    
    Args:
        price_dict: Dictionary mapping ticker to OHLCV DataFrame
        min_avg_volume: Minimum average daily volume
        min_avg_value: Minimum average daily traded value (₹)
        lookback_days: Number of days to calculate average
        
    Returns:
        List of liquid tickers
    """
    liquid_tickers = []
    
    for ticker, df in price_dict.items():
        if df.empty or len(df) < lookback_days:
            continue
        
        recent_data = df.tail(lookback_days)
        
        # Check volume
        avg_volume = recent_data['Volume'].mean()
        if avg_volume < min_avg_volume:
            continue
        
        # Check traded value
        if 'Close' in recent_data.columns:
            avg_price = recent_data['Close'].mean()
            avg_value = avg_volume * avg_price
            if avg_value < min_avg_value:
                continue
        
        liquid_tickers.append(ticker)
    
    logger.info(f"Liquid stocks: {len(liquid_tickers)}/{len(price_dict)}")
    return liquid_tickers


def filter_fo_eligible(tickers: List[str]) -> List[str]:
    """
    Filter stocks that are F&O eligible.
    
    Args:
        tickers: List of tickers
        
    Returns:
        List of F&O eligible tickers
    """
    fo_tickers = []
    
    for ticker in tickers:
        clean = ticker.replace(".NS", "").replace(".BO", "").upper()
        if clean in FO_ELIGIBLE_STOCKS:
            fo_tickers.append(ticker)
    
    logger.info(f"F&O eligible: {len(fo_tickers)}/{len(tickers)}")
    return fo_tickers


def filter_not_in_circuit(
    price_dict: Dict[str, pd.DataFrame],
    circuit_threshold: float = 0.95
) -> List[str]:
    """
    Filter out stocks that are near circuit limits.
    
    Args:
        price_dict: Dictionary mapping ticker to OHLCV DataFrame
        circuit_threshold: Threshold as fraction of circuit limit
        
    Returns:
        List of tickers not near circuit
    """
    valid_tickers = []
    
    for ticker, df in price_dict.items():
        if df.empty or len(df) < 2:
            continue
        
        clean = ticker.replace(".NS", "").replace(".BO", "").upper()
        
        # Determine circuit band
        category = "A" if clean in STOCK_CATEGORIES["A"] else "default"
        band = CIRCUIT_BANDS.get(category, CIRCUIT_BANDS["default"])
        
        # Get recent prices
        latest_close = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2]
        
        # Calculate change
        change_pct = abs(latest_close - prev_close) / prev_close
        
        # Check if near circuit
        if change_pct < band * circuit_threshold:
            valid_tickers.append(ticker)
    
    logger.info(f"Not in circuit: {len(valid_tickers)}/{len(price_dict)}")
    return valid_tickers


def get_circuit_band(ticker: str) -> float:
    """
    Get circuit band for a stock.
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Circuit band as decimal (e.g., 0.20 for ±20%)
    """
    clean = ticker.replace(".NS", "").replace(".BO", "").upper()
    
    for category, stocks in STOCK_CATEGORIES.items():
        if clean in stocks:
            return CIRCUIT_BANDS.get(category, CIRCUIT_BANDS["default"])
    
    return CIRCUIT_BANDS["default"]


def check_circuit_status(
    ticker: str,
    current_price: float,
    prev_close: float
) -> Dict:
    """
    Check if a stock is near circuit limits.
    
    Args:
        ticker: Stock symbol
        current_price: Current price
        prev_close: Previous close price
        
    Returns:
        Dictionary with circuit status
    """
    band = get_circuit_band(ticker)
    
    upper_limit = prev_close * (1 + band)
    lower_limit = prev_close * (1 - band)
    
    change_pct = (current_price - prev_close) / prev_close
    
    # Distance to limits
    dist_to_upper = (upper_limit - current_price) / prev_close
    dist_to_lower = (current_price - lower_limit) / prev_close
    
    near_circuit = dist_to_upper < 0.02 or dist_to_lower < 0.02
    
    return {
        'ticker': ticker,
        'band': band,
        'upper_limit': upper_limit,
        'lower_limit': lower_limit,
        'current_price': current_price,
        'change_pct': change_pct,
        'dist_to_upper': dist_to_upper,
        'dist_to_lower': dist_to_lower,
        'near_circuit': near_circuit,
        'at_upper_circuit': current_price >= upper_limit * 0.999,
        'at_lower_circuit': current_price <= lower_limit * 1.001,
    }


def filter_by_price_range(
    price_dict: Dict[str, pd.DataFrame],
    min_price: float = 10.0,
    max_price: float = 50000.0
) -> List[str]:
    """
    Filter stocks by price range.
    
    Args:
        price_dict: Dictionary mapping ticker to OHLCV DataFrame
        min_price: Minimum price
        max_price: Maximum price
        
    Returns:
        List of tickers within price range
    """
    valid_tickers = []
    
    for ticker, df in price_dict.items():
        if df.empty:
            continue
        
        latest_price = df['Close'].iloc[-1]
        
        if min_price <= latest_price <= max_price:
            valid_tickers.append(ticker)
    
    logger.info(f"Price range filter: {len(valid_tickers)}/{len(price_dict)}")
    return valid_tickers


def create_universe(
    price_dict: Dict[str, pd.DataFrame],
    min_liquidity: bool = True,
    fo_only: bool = False,
    check_circuit: bool = True,
    price_range: Optional[tuple] = None
) -> List[str]:
    """
    Create a filtered universe of stocks.
    
    Args:
        price_dict: Dictionary mapping ticker to OHLCV DataFrame
        min_liquidity: Whether to apply liquidity filter
        fo_only: Whether to include only F&O stocks
        check_circuit: Whether to filter out stocks near circuit
        price_range: Optional (min, max) price tuple
        
    Returns:
        List of tickers in universe
    """
    tickers = list(price_dict.keys())
    
    # Apply filters
    if min_liquidity:
        tickers = filter_liquid_stocks(
            {t: price_dict[t] for t in tickers}
        )
    
    if fo_only:
        tickers = filter_fo_eligible(tickers)
    
    if check_circuit:
        tickers = filter_not_in_circuit(
            {t: price_dict[t] for t in tickers}
        )
    
    if price_range:
        tickers = filter_by_price_range(
            {t: price_dict[t] for t in tickers},
            min_price=price_range[0],
            max_price=price_range[1]
        )
    
    logger.info(f"Final universe: {len(tickers)} stocks")
    return tickers


if __name__ == "__main__":
    # Test the module
    logging.basicConfig(level=logging.INFO)
    
    # Create sample data
    sample_data = {
        "RELIANCE.NS": pd.DataFrame({
            'Close': [2500, 2520, 2540, 2550, 2560],
            'Volume': [5000000, 5500000, 5200000, 5800000, 6000000]
        }),
        "TCS.NS": pd.DataFrame({
            'Close': [3500, 3520, 3540, 3550, 3560],
            'Volume': [2000000, 2200000, 2100000, 2300000, 2400000]
        }),
        "ILLIQUID.NS": pd.DataFrame({
            'Close': [100, 102, 101, 103, 102],
            'Volume': [1000, 1200, 1100, 1300, 1200]  # Too low
        }),
    }
    
    print("=== Test filter_liquid_stocks ===")
    liquid = filter_liquid_stocks(sample_data, min_avg_volume=100000)
    print(f"Liquid tickers: {liquid}")
    
    print("\n=== Test filter_fo_eligible ===")
    fo = filter_fo_eligible(list(sample_data.keys()))
    print(f"F&O eligible: {fo}")
    
    print("\n=== Test get_circuit_band ===")
    for ticker in sample_data.keys():
        band = get_circuit_band(ticker)
        print(f"{ticker}: ±{band*100:.0f}%")
    
    print("\n=== Test create_universe ===")
    universe = create_universe(sample_data, min_liquidity=True, fo_only=False)
    print(f"Final universe: {universe}")
