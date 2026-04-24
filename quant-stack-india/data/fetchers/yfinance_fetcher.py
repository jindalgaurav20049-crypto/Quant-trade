"""
yfinance-based OHLCV fetcher for Indian markets.

Handles NSE (.NS) and BSE (.BO) ticker suffixes automatically.
"""

import time
import logging
from typing import Dict, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)


def _add_suffix(ticker: str) -> str:
    """Add .NS suffix if no suffix present."""
    ticker = ticker.upper().strip()
    if not ticker.endswith('.NS') and not ticker.endswith('.BO'):
        return f"{ticker}.NS"
    return ticker


def fetch_ohlcv(
    ticker: str,
    period: str = "2y",
    interval: str = "1d"
) -> pd.DataFrame:
    """
    Fetch OHLCV data for a single ticker.
    
    Args:
        ticker: Stock symbol (e.g., "RELIANCE" or "RELIANCE.NS")
        period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        
    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
        Returns empty DataFrame with correct columns on failure.
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed. Run: pip install yfinance==0.2.36")
        return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
    
    # Try with .NS suffix first, then .BO on failure
    ticker_ns = _add_suffix(ticker)
    ticker_bo = ticker_ns.replace('.NS', '.BO')
    
    for ticker_try in [ticker_ns, ticker_bo]:
        try:
            logger.debug(f"Fetching {ticker_try} (period={period}, interval={interval})")
            stock = yf.Ticker(ticker_try)
            data = stock.history(period=period, interval=interval)
            
            if data.empty:
                logger.warning(f"Empty data for {ticker_try}")
                continue
            
            # Remove timezone info from index
            data.index = data.index.tz_localize(None)
            
            # Keep only OHLCV columns (drop Adj Close, Dividends, Stock Splits)
            columns_to_keep = ['Open', 'High', 'Low', 'Close', 'Volume']
            data = data[[c for c in columns_to_keep if c in data.columns]]
            
            # Drop rows where Volume == 0 (NSE holiday artifacts)
            if 'Volume' in data.columns:
                data = data[data['Volume'] > 0]
            
            logger.info(f"Fetched {ticker_try}: {len(data)} rows")
            return data
            
        except Exception as e:
            logger.warning(f"Failed to fetch {ticker_try}: {e}")
            continue
    
    logger.error(f"Failed to fetch data for {ticker} from both NSE and BSE")
    return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])


def fetch_multiple(
    tickers: List[str],
    period: str = "2y",
    interval: str = "1d",
    delay: float = 0.5
) -> Dict[str, pd.DataFrame]:
    """
    Fetch OHLCV data for multiple tickers.
    
    Args:
        tickers: List of stock symbols
        period: Data period
        interval: Data interval
        delay: Delay between requests (seconds) to avoid rate limiting
        
    Returns:
        Dictionary mapping ticker to DataFrame
    """
    results = {}
    
    for i, ticker in enumerate(tickers):
        results[ticker] = fetch_ohlcv(ticker, period, interval)
        
        # Rate limiting delay (except for last ticker)
        if i < len(tickers) - 1 and delay > 0:
            time.sleep(delay)
    
    # Log summary
    valid_count = sum(1 for df in results.values() if not df.empty)
    logger.info(f"Fetched data for {valid_count}/{len(tickers)} tickers")
    
    return results


def fetch_index(index: str = "^NSEI", period: str = "2y") -> pd.DataFrame:
    """
    Fetch index data (e.g., Nifty 50, Bank Nifty).
    
    Args:
        index: Index symbol (^NSEI for Nifty 50, ^NSEBANK for Bank Nifty)
        period: Data period
        
    Returns:
        DataFrame with OHLCV data
    """
    return fetch_ohlcv(index, period=period)


def fetch_india_vix(period: str = "2y") -> pd.DataFrame:
    """
    Fetch India VIX data.
    
    Args:
        period: Data period
        
    Returns:
        DataFrame with VIX data
    """
    return fetch_ohlcv("^INDIAVIX", period=period)


def fetch_stock_info(ticker: str) -> Dict:
    """
    Fetch stock information (market cap, P/E, etc.).
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Dictionary with stock info
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed")
        return {}
    
    ticker_ns = _add_suffix(ticker)
    
    try:
        stock = yf.Ticker(ticker_ns)
        info = stock.info
        return info
    except Exception as e:
        logger.error(f"Failed to fetch info for {ticker}: {e}")
        return {}


def fetch_fundamentals(ticker: str) -> Dict:
    """
    Fetch fundamental data (P/E, P/B, ROE, etc.).
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Dictionary with fundamental metrics
    """
    info = fetch_stock_info(ticker)
    
    fundamentals = {
        'market_cap': info.get('marketCap'),
        'pe_ratio': info.get('trailingPE'),
        'forward_pe': info.get('forwardPE'),
        'pb_ratio': info.get('priceToBook'),
        'roe': info.get('returnOnEquity'),
        'roa': info.get('returnOnAssets'),
        'debt_to_equity': info.get('debtToEquity'),
        'current_ratio': info.get('currentRatio'),
        'dividend_yield': info.get('dividendYield'),
        'eps': info.get('trailingEps'),
        'revenue_growth': info.get('revenueGrowth'),
        'earnings_growth': info.get('earningsGrowth'),
        'sector': info.get('sector'),
        'industry': info.get('industry'),
    }
    
    return fundamentals


if __name__ == "__main__":
    # Test the module
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test fetch_ohlcv ===")
    data = fetch_ohlcv("RELIANCE", period="5d")
    print(data.head())
    
    print("\n=== Test fetch_multiple ===")
    tickers = ["RELIANCE", "TCS", "HDFCBANK"]
    multi_data = fetch_multiple(tickers, period="5d")
    for t, df in multi_data.items():
        print(f"{t}: {len(df)} rows")
    
    print("\n=== Test fetch_index ===")
    nifty = fetch_index("^NSEI", period="5d")
    print(f"Nifty 50: {len(nifty)} rows")
    
    print("\n=== Test fetch_india_vix ===")
    vix = fetch_india_vix(period="5d")
    print(f"India VIX: {len(vix)} rows")
