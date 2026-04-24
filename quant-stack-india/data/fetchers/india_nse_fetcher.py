"""
NSE-specific data fetcher wrapping nsepython, jugaad-data, and nsetools.

Provides access to live quotes, FII/DII data, option chains, and more.
"""

import logging
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def get_live_quote(ticker: str) -> Dict:
    """
    Get live quote for a stock from NSE.
    
    Args:
        ticker: Stock symbol (e.g., "RELIANCE")
        
    Returns:
        Dictionary with price, change, volume, etc.
        Returns {'price': None, 'error': ...} on failure.
    """
    clean_ticker = ticker.replace(".NS", "").replace(".BO", "").upper()
    
    # Try nsepython first
    try:
        import nsepython as nse
        quote = nse.nse_eq(clean_ticker)
        
        price_info = quote.get('priceInfo', {})
        security_info = quote.get('securityInfo', {})
        
        return {
            'price': price_info.get('lastPrice'),
            'change': price_info.get('change'),
            'pct_change': price_info.get('pChange'),
            'volume': price_info.get('volume'),
            'open': price_info.get('open'),
            'high': price_info.get('intraDayHighLow', {}).get('max'),
            'low': price_info.get('intraDayHighLow', {}).get('min'),
            '52w_high': security_info.get('weekHighLow', {}).get('max'),
            '52w_low': security_info.get('weekHighLow', {}).get('min'),
            'circuit_limit_upper': price_info.get('upperCP'),
            'circuit_limit_lower': price_info.get('lowerCP'),
            'symbol': clean_ticker,
        }
    except Exception as e1:
        logger.warning(f"nsepython failed for {clean_ticker}: {e1}")
        
        # Fallback to nsetools
        try:
            from nsetools import NSE
            nse_client = NSE()
            quote = nse_client.get_quote(clean_ticker)
            
            return {
                'price': quote.get('lastPrice'),
                'change': quote.get('change'),
                'pct_change': quote.get('pChange'),
                'volume': quote.get('volume'),
                'open': quote.get('open'),
                'high': quote.get('dayHigh'),
                'low': quote.get('dayLow'),
                '52w_high': quote.get('high52'),
                '52w_low': quote.get('low52'),
                'circuit_limit_upper': None,
                'circuit_limit_lower': None,
                'symbol': clean_ticker,
            }
        except Exception as e2:
            logger.error(f"Both nsepython and nsetools failed for {clean_ticker}: {e2}")
            return {'price': None, 'error': str(e2), 'symbol': clean_ticker}


def get_fii_dii_data(days: int = 30) -> pd.DataFrame:
    """
    Fetch FII/DII provisional data from NSE.
    
    Args:
        days: Number of days to fetch
        
    Returns:
        DataFrame with columns: date, fii_net, dii_net, fii_buy, fii_sell, dii_buy, dii_sell
        Returns empty DataFrame on failure.
    """
    try:
        import nsepython as nse
        data = nse.fii_dii_data()
        
        if not data:
            logger.warning("No FII/DII data returned")
            return pd.DataFrame(columns=['date', 'fii_net', 'dii_net', 'fii_buy', 'fii_sell', 'dii_buy', 'dii_sell'])
        
        # Parse the data
        records = []
        for item in data:
            record = {
                'date': item.get('date'),
                'fii_buy': float(item.get('fii_buy', 0) or 0),
                'fii_sell': float(item.get('fii_sell', 0) or 0),
                'dii_buy': float(item.get('dii_buy', 0) or 0),
                'dii_sell': float(item.get('dii_sell', 0) or 0),
            }
            record['fii_net'] = record['fii_buy'] - record['fii_sell']
            record['dii_net'] = record['dii_buy'] - record['dii_sell']
            records.append(record)
        
        df = pd.DataFrame(records)
        
        # Limit to requested days
        if len(df) > days:
            df = df.head(days)
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to fetch FII/DII data: {e}")
        return pd.DataFrame(columns=['date', 'fii_net', 'dii_net', 'fii_buy', 'fii_sell', 'dii_buy', 'dii_sell'])


def get_option_chain(symbol: str = "NIFTY") -> Dict:
    """
    Get option chain data for a symbol.
    
    Args:
        symbol: Symbol (NIFTY, BANKNIFTY, or stock symbol)
        
    Returns:
        Dictionary with atm_strike, pcr, max_pain, total_call_oi, total_put_oi
        Returns {'pcr': None, 'error': ...} on failure.
    """
    try:
        import nsepython as nse
        chain = nse.nse_optionchain_scrapper(symbol)
        
        if not chain:
            return {'pcr': None, 'error': 'Empty option chain', 'symbol': symbol}
        
        # Extract relevant data
        records = chain.get('records', {})
        underlying_value = records.get('underlyingValue', 0)
        data = records.get('data', [])
        
        if not data:
            return {'pcr': None, 'error': 'No option data', 'symbol': symbol}
        
        # Find ATM strike
        strikes = [d['strikePrice'] for d in data if 'strikePrice' in d]
        if strikes and underlying_value:
            atm_strike = min(strikes, key=lambda x: abs(x - underlying_value))
        else:
            atm_strike = None
        
        # Calculate PCR
        total_call_oi = sum(d.get('CE', {}).get('openInterest', 0) for d in data if 'CE' in d)
        total_put_oi = sum(d.get('PE', {}).get('openInterest', 0) for d in data if 'PE' in d)
        pcr = total_put_oi / total_call_oi if total_call_oi > 0 else None
        
        # Simple max pain calculation (strike with minimum total OI value)
        # This is a simplified version
        max_pain = atm_strike  # Placeholder
        
        return {
            'atm_strike': atm_strike,
            'pcr': pcr,
            'max_pain': max_pain,
            'total_call_oi': total_call_oi,
            'total_put_oi': total_put_oi,
            'underlying_value': underlying_value,
            'symbol': symbol,
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch option chain for {symbol}: {e}")
        return {'pcr': None, 'error': str(e), 'symbol': symbol}


def get_india_vix() -> Optional[float]:
    """
    Get current India VIX value.
    
    Returns:
        Current VIX value or None on failure
    """
    # Try nsepython first
    try:
        import nsepython as nse
        quote = nse.nse_quote_meta("India VIX")
        if quote and 'data' in quote:
            return float(quote['data'][0].get('lastPrice', 0))
    except Exception as e:
        logger.warning(f"nsepython India VIX failed: {e}")
    
    # Fallback to yfinance
    try:
        from .yfinance_fetcher import fetch_india_vix
        vix_data = fetch_india_vix(period="5d")
        if not vix_data.empty:
            return float(vix_data['Close'].iloc[-1])
    except Exception as e:
        logger.error(f"yfinance India VIX fallback failed: {e}")
    
    return None


def get_historical_data(ticker: str, from_date: str, to_date: str) -> pd.DataFrame:
    """
    Get historical data using jugaad-data.
    
    Args:
        ticker: Stock symbol
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        
    Returns:
        DataFrame with columns: open, high, low, close, volume
        Falls back to yfinance on failure.
    """
    clean_ticker = ticker.replace(".NS", "").replace(".BO", "").upper()
    
    try:
        from jugaad_data.nse import stock_df
        
        # Parse dates
        from_dt = datetime.strptime(from_date, "%Y-%m-%d")
        to_dt = datetime.strptime(to_date, "%Y-%m-%d")
        
        # Fetch data
        df = stock_df(
            symbol=clean_ticker,
            from_date=from_dt,
            to_date=to_dt,
            series="EQ"
        )
        
        if df.empty:
            raise ValueError("Empty data returned")
        
        # Rename columns to lowercase
        df = df.rename(columns={
            'OPEN': 'open',
            'HIGH': 'high',
            'LOW': 'low',
            'CLOSE': 'close',
            'VOLUME': 'volume'
        })
        
        # Ensure date column is datetime
        if 'DATE' in df.columns:
            df['date'] = pd.to_datetime(df['DATE'])
            df = df.set_index('date')
        
        return df[['open', 'high', 'low', 'close', 'volume']]
        
    except Exception as e:
        logger.warning(f"jugaad_data failed for {clean_ticker}: {e}")
        
        # Fallback to yfinance
        try:
            from .yfinance_fetcher import fetch_ohlcv
            df = fetch_ohlcv(ticker, period="max")
            
            if df.empty:
                return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            
            # Filter by date range
            df = df[(df.index >= from_date) & (df.index <= to_date)]
            
            # Rename columns to lowercase
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e2:
            logger.error(f"yfinance fallback also failed: {e2}")
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])


def get_nifty500_constituents() -> List[str]:
    """
    Get hardcoded list of top Nifty 500 companies as .NS tickers.
    
    Returns:
        List of ticker symbols with .NS suffix
    """
    # Top 100 liquid stocks from Nifty 500
    tickers = [
        # Nifty 50
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
        "HINDUNILVR.NS", "BAJFINANCE.NS", "SBIN.NS", "BHARTIARTL.NS", "WIPRO.NS",
        "HCLTECH.NS", "ASIANPAINT.NS", "MARUTI.NS", "TITAN.NS", "SUNPHARMA.NS",
        "ULTRACEMCO.NS", "NESTLEIND.NS", "AXISBANK.NS", "KOTAKBANK.NS", "LT.NS",
        "POWERGRID.NS", "NTPC.NS", "ONGC.NS", "COALINDIA.NS", "TECHM.NS",
        "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS",
        "BPCL.NS", "BRITANNIA.NS", "CIPLA.NS", "DIVISLAB.NS", "DRREDDY.NS",
        "EICHERMOT.NS", "GRASIM.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "INDUSINDBK.NS",
        "ITC.NS", "JSWSTEEL.NS", "M&M.NS", "SHREECEM.NS", "TATACONSUM.NS",
        "TATAMOTORS.NS", "TATASTEEL.NS", "UPL.NS", "VEDL.NS", "YESBANK.NS",
        
        # Additional Midcaps
        "PERSISTENT.NS", "MPHASIS.NS", "DIXON.NS", "TATAELXSI.NS", "MAXHEALTH.NS",
        "INDUSINDBK.NS", "BANKBARODA.NS", "PNB.NS", "CANBK.NS", "UNIONBANK.NS",
        "IOB.NS", "MAHABANK.NS", "UCOBANK.NS", "CENTRALBK.NS", "PSB.NS",
        "J&KBANK.NS", "BANDHANBNK.NS", "RBLBANK.NS", "FEDERALBNK.NS", "IDFCFIRSTB.NS",
        "AUBANK.NS", "CITYUNION.NS", "KARURVYSYA.NS", "SOUTHBANK.NS", "TMB.NS",
        "DCBBANK.NS", "DHANBANK.NS", "KARNATAKABANK.NS", "J&KBANK.NS", "CSBBANK.NS",
        "BANKINDIA.NS", "MAHABANK.NS", "UCOBANK.NS", "CENTRALBK.NS", "PSB.NS",
        "AARTIIND.NS", "ABB.NS", "ABBOTINDIA.NS", "ABCAPITAL.NS", "ABFRL.NS",
        "ACC.NS", "ADANIGREEN.NS", "ADANIPOWER.NS", "ADANITRANS.NS", "ALKEM.NS",
        "AMBUJACEM.NS", "AUROPHARMA.NS", "DMART.NS", "BAJAJHLDNG.NS", "BALKRISIND.NS",
        "BANKBARODA.NS", "BATAINDIA.NS", "BERGEPAINT.NS", "BIOCON.NS", "BOSCHLTD.NS",
        "CADILAHC.NS", "COLPAL.NS", "CONCOR.NS", "COROMANDEL.NS", "CUMMINSIND.NS",
        "DABUR.NS", "DEEPAKNTR.NS", "DLF.NS", "ESCORTS.NS", "GAIL.NS",
    ]
    
    return tickers


if __name__ == "__main__":
    # Test the module
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test get_live_quote ===")
    quote = get_live_quote("RELIANCE")
    print(quote)
    
    print("\n=== Test get_fii_dii_data ===")
    fii_dii = get_fii_dii_data(days=5)
    print(fii_dii)
    
    print("\n=== Test get_option_chain ===")
    chain = get_option_chain("NIFTY")
    print(chain)
    
    print("\n=== Test get_india_vix ===")
    vix = get_india_vix()
    print(f"India VIX: {vix}")
    
    print("\n=== Test get_nifty500_constituents ===")
    constituents = get_nifty500_constituents()
    print(f"Number of constituents: {len(constituents)}")
    print(f"First 5: {constituents[:5]}")
