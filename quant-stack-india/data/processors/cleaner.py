"""
Data cleaning utilities for OHLCV data.

Handles missing values, outliers, and split/dividend adjustments.
"""

import logging
from typing import Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def clean_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean OHLCV data by removing invalid rows and handling edge cases.
    
    Args:
        df: Raw OHLCV DataFrame
        
    Returns:
        Cleaned DataFrame
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    # Remove rows with zero or negative prices
    price_cols = ['Open', 'High', 'Low', 'Close']
    for col in price_cols:
        if col in df.columns:
            df = df[df[col] > 0]
    
    # Remove rows with zero volume
    if 'Volume' in df.columns:
        df = df[df['Volume'] > 0]
    
    # Ensure High >= Low
    if 'High' in df.columns and 'Low' in df.columns:
        df = df[df['High'] >= df['Low']]
    
    # Ensure High >= Close >= Low
    if all(c in df.columns for c in ['High', 'Close', 'Low']):
        df = df[(df['High'] >= df['Close']) & (df['Close'] >= df['Low'])]
    
    # Ensure High >= Open >= Low
    if all(c in df.columns for c in ['High', 'Open', 'Low']):
        df = df[(df['High'] >= df['Open']) & (df['Open'] >= df['Low'])]
    
    # Remove duplicates
    df = df[~df.index.duplicated(keep='first')]
    
    # Sort by date
    df = df.sort_index()
    
    logger.info(f"Cleaned data: {len(df)} rows remaining")
    return df


def handle_missing_values(
    df: pd.DataFrame,
    method: str = "forward_fill"
) -> pd.DataFrame:
    """
    Handle missing values in OHLCV data.
    
    Args:
        df: DataFrame with potential missing values
        method: Method to use ("forward_fill", "interpolate", "drop")
        
    Returns:
        DataFrame with missing values handled
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    # Count missing values before
    missing_before = df.isnull().sum().sum()
    
    if method == "forward_fill":
        df = df.fillna(method='ffill')
        # Fill any remaining NaN at the start with backward fill
        df = df.fillna(method='bfill')
    elif method == "interpolate":
        df = df.interpolate(method='linear')
        # Fill any remaining NaN at edges
        df = df.fillna(method='ffill').fillna(method='bfill')
    elif method == "drop":
        df = df.dropna()
    else:
        logger.warning(f"Unknown method {method}, using forward_fill")
        df = df.fillna(method='ffill').fillna(method='bfill')
    
    missing_after = df.isnull().sum().sum()
    logger.info(f"Missing values: {missing_before} -> {missing_after}")
    
    return df


def detect_outliers(
    df: pd.DataFrame,
    column: str = "Close",
    method: str = "zscore",
    threshold: float = 3.0
) -> pd.Series:
    """
    Detect outliers in a price series.
    
    Args:
        df: DataFrame with price data
        column: Column to check for outliers
        method: Method to use ("zscore", "iqr", "pct_change")
        threshold: Threshold for outlier detection
        
    Returns:
        Boolean Series indicating outliers
    """
    if df.empty or column not in df.columns:
        return pd.Series(False, index=df.index)
    
    data = df[column]
    
    if method == "zscore":
        z_scores = np.abs((data - data.mean()) / data.std())
        return z_scores > threshold
    
    elif method == "iqr":
        q1 = data.quantile(0.25)
        q3 = data.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        return (data < lower_bound) | (data > upper_bound)
    
    elif method == "pct_change":
        pct_changes = data.pct_change().abs()
        return pct_changes > threshold
    
    else:
        logger.warning(f"Unknown method {method}")
        return pd.Series(False, index=df.index)


def remove_outliers(
    df: pd.DataFrame,
    column: str = "Close",
    method: str = "zscore",
    threshold: float = 3.0
) -> pd.DataFrame:
    """
    Remove outlier rows from DataFrame.
    
    Args:
        df: DataFrame with potential outliers
        column: Column to check
        method: Detection method
        threshold: Threshold for detection
        
    Returns:
        DataFrame with outliers removed
    """
    outliers = detect_outliers(df, column, method, threshold)
    cleaned = df[~outliers]
    
    removed_count = outliers.sum()
    logger.info(f"Removed {removed_count} outliers ({removed_count/len(df)*100:.2f}%)")
    
    return cleaned


def adjust_for_splits(
    df: pd.DataFrame,
    split_ratio: float,
    split_date: str
) -> pd.DataFrame:
    """
    Adjust OHLCV data for stock splits.
    
    Args:
        df: OHLCV DataFrame
        split_ratio: Split ratio (e.g., 2 for 2:1 split)
        split_date: Date of split (YYYY-MM-DD)
        
    Returns:
        Adjusted DataFrame
    """
    if df.empty:
        return df
    
    df = df.copy()
    split_dt = pd.to_datetime(split_date)
    
    # Adjust prices before split date
    mask = df.index < split_dt
    price_cols = ['Open', 'High', 'Low', 'Close']
    
    for col in price_cols:
        if col in df.columns:
            df.loc[mask, col] = df.loc[mask, col] / split_ratio
    
    # Adjust volume
    if 'Volume' in df.columns:
        df.loc[mask, 'Volume'] = df.loc[mask, 'Volume'] * split_ratio
    
    logger.info(f"Adjusted for {split_ratio}:1 split on {split_date}")
    return df


def resample_ohlcv(
    df: pd.DataFrame,
    rule: str = "W"
) -> pd.DataFrame:
    """
    Resample OHLCV data to a different timeframe.
    
    Args:
        df: OHLCV DataFrame
        rule: Resampling rule ("W"=weekly, "M"=monthly, "Q"=quarterly)
        
    Returns:
        Resampled DataFrame
    """
    if df.empty:
        return df
    
    resampled = pd.DataFrame()
    
    if 'Open' in df.columns:
        resampled['Open'] = df['Open'].resample(rule).first()
    if 'High' in df.columns:
        resampled['High'] = df['High'].resample(rule).max()
    if 'Low' in df.columns:
        resampled['Low'] = df['Low'].resample(rule).min()
    if 'Close' in df.columns:
        resampled['Close'] = df['Close'].resample(rule).last()
    if 'Volume' in df.columns:
        resampled['Volume'] = df['Volume'].resample(rule).sum()
    
    return resampled.dropna()


def calculate_returns(
    df: pd.DataFrame,
    column: str = "Close",
    periods: int = 1
) -> pd.Series:
    """
    Calculate returns for a price series.
    
    Args:
        df: DataFrame with price data
        column: Price column
        periods: Number of periods for return calculation
        
    Returns:
        Series of returns
    """
    if column not in df.columns:
        return pd.Series(index=df.index)
    
    return df[column].pct_change(periods=periods)


def merge_price_data(
    price_dict: dict,
    column: str = "Close"
) -> pd.DataFrame:
    """
    Merge close prices from multiple tickers into a single DataFrame.
    
    Args:
        price_dict: Dictionary mapping ticker to OHLCV DataFrame
        column: Column to extract (default: Close)
        
    Returns:
        DataFrame with tickers as columns and dates as index
    """
    merged = pd.DataFrame()
    
    for ticker, df in price_dict.items():
        if not df.empty and column in df.columns:
            merged[ticker] = df[column]
    
    return merged.dropna(how='all')


if __name__ == "__main__":
    # Test the module
    logging.basicConfig(level=logging.INFO)
    
    # Create sample data
    dates = pd.date_range("2024-01-01", periods=20, freq='D')
    sample_data = pd.DataFrame({
        'Open': np.random.randn(20).cumsum() + 100,
        'High': np.random.randn(20).cumsum() + 102,
        'Low': np.random.randn(20).cumsum() + 98,
        'Close': np.random.randn(20).cumsum() + 100,
        'Volume': np.random.randint(1000, 10000, 20)
    }, index=dates)
    
    # Introduce some issues
    sample_data.loc[dates[5], 'Close'] = 0  # Invalid price
    sample_data.loc[dates[10], 'Volume'] = 0  # Zero volume
    
    print("=== Original data ===")
    print(sample_data.head(10))
    
    print("\n=== Cleaned data ===")
    cleaned = clean_ohlcv(sample_data)
    print(cleaned.head(10))
    
    print("\n=== Detect outliers ===")
    outliers = detect_outliers(cleaned, method="zscore")
    print(f"Outliers detected: {outliers.sum()}")
