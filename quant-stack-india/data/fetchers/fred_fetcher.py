"""
FRED (Federal Reserve Economic Data) fetcher for macro indicators.

Provides access to global rates, DXY, and other macro data.
"""

import os
import logging
from typing import Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)


def get_fred_api_key() -> Optional[str]:
    """Get FRED API key from environment."""
    return os.getenv("FRED_API_KEY")


def fetch_fred_data(
    series_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetch data from FRED.
    
    Args:
        series_id: FRED series ID (e.g., "DGS10" for 10-year Treasury)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        
    Returns:
        DataFrame with date index and value column
        Returns empty DataFrame on failure.
    """
    api_key = get_fred_api_key()
    
    if not api_key or api_key == "your_fred_key_here":
        logger.warning("FRED_API_KEY not set — returning empty DataFrame")
        return pd.DataFrame(columns=['value'])
    
    try:
        from fredapi import Fred
        
        fred = Fred(api_key=api_key)
        data = fred.get_series(series_id, start_date, end_date)
        
        if data is None or data.empty:
            logger.warning(f"No data returned for {series_id}")
            return pd.DataFrame(columns=['value'])
        
        df = pd.DataFrame({'value': data})
        df.index.name = 'date'
        
        logger.info(f"Fetched {series_id}: {len(df)} rows")
        return df
        
    except Exception as e:
        logger.error(f"Failed to fetch {series_id}: {e}")
        return pd.DataFrame(columns=['value'])


def fetch_macro_indicators() -> Dict[str, pd.DataFrame]:
    """
    Fetch key macroeconomic indicators.
    
    Returns:
        Dictionary mapping indicator name to DataFrame
    """
    indicators = {
        'us_10y_yield': 'DGS10',           # 10-Year Treasury Constant Maturity Rate
        'us_2y_yield': 'DGS2',             # 2-Year Treasury Constant Maturity Rate
        'fed_funds_rate': 'DFF',           # Federal Funds Effective Rate
        'dxy': 'DTWEXBGS',                 # Trade Weighted U.S. Dollar Index
        'us_cpi_yoy': 'CPIAUCSL',          # Consumer Price Index (needs YoY calc)
        'us_unemployment': 'UNRATE',       # Unemployment Rate
        'us_gdp_growth': 'A191RL1Q225SBEA', # Real Gross Domestic Product (percent change)
        'vix': 'VIXCLS',                   # CBOE Volatility Index
        'brent_crude': 'DCOILBRENTEU',     # Brent Crude Oil Price
        'gold_price': 'GOLDAMGBD228NLBM',  # Gold Fixing Price
    }
    
    results = {}
    
    for name, series_id in indicators.items():
        df = fetch_fred_data(series_id, start_date="2020-01-01")
        if not df.empty:
            results[name] = df
    
    return results


def fetch_yield_curve() -> pd.DataFrame:
    """
    Fetch US Treasury yield curve data.
    
    Returns:
        DataFrame with various maturity yields
    """
    maturities = {
        '1m': 'DGS1MO',
        '3m': 'DGS3MO',
        '6m': 'DGS6MO',
        '1y': 'DGS1',
        '2y': 'DGS2',
        '5y': 'DGS5',
        '10y': 'DGS10',
        '30y': 'DGS30',
    }
    
    dfs = []
    
    for maturity, series_id in maturities.items():
        df = fetch_fred_data(series_id, start_date="2020-01-01")
        if not df.empty:
            df = df.rename(columns={'value': maturity})
            dfs.append(df)
    
    if dfs:
        # Join all dataframes on date index
        result = dfs[0]
        for df in dfs[1:]:
            result = result.join(df, how='outer')
        return result
    
    return pd.DataFrame()


def calculate_yield_curve_spread(
    long_maturity: str = "DGS10",
    short_maturity: str = "DGS2"
) -> pd.DataFrame:
    """
    Calculate yield curve spread (e.g., 10Y-2Y).
    
    Args:
        long_maturity: Long maturity series ID
        short_maturity: Short maturity series ID
        
    Returns:
        DataFrame with spread values
    """
    long_df = fetch_fred_data(long_maturity, start_date="2020-01-01")
    short_df = fetch_fred_data(short_maturity, start_date="2020-01-01")
    
    if long_df.empty or short_df.empty:
        return pd.DataFrame(columns=['spread'])
    
    # Join and calculate spread
    combined = long_df.join(short_df, how='inner', lsuffix='_long', rsuffix='_short')
    combined['spread'] = combined['value_long'] - combined['value_short']
    
    return combined[['spread']]


if __name__ == "__main__":
    # Test the module
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test fetch_fred_data ===")
    data = fetch_fred_data("DGS10", start_date="2024-01-01")
    print(data.tail())
    
    print("\n=== Test fetch_macro_indicators ===")
    macro = fetch_macro_indicators()
    for name, df in macro.items():
        print(f"{name}: {len(df)} rows")
    
    print("\n=== Test fetch_yield_curve ===")
    curve = fetch_yield_curve()
    print(curve.tail())
    
    print("\n=== Test calculate_yield_curve_spread ===")
    spread = calculate_yield_curve_spread("DGS10", "DGS2")
    print(spread.tail())
