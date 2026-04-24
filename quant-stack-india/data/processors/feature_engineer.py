"""
Feature engineering for Indian markets.

Adds technical indicators and India-specific features like FII/DII flows,
India VIX, and PCR (put-call ratio).
"""

import logging
from typing import Optional, List
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def add_technical_indicators(
    df: pd.DataFrame,
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    bb_window: int = 20,
    bb_std: float = 2.0,
    atr_period: int = 14
) -> pd.DataFrame:
    """
    Add technical indicators to OHLCV data.
    
    Args:
        df: OHLCV DataFrame
        rsi_period: RSI lookback period
        macd_fast: MACD fast period
        macd_slow: MACD slow period
        macd_signal: MACD signal period
        bb_window: Bollinger Bands window
        bb_std: Bollinger Bands standard deviation
        atr_period: ATR period
        
    Returns:
        DataFrame with added indicator columns
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    try:
        import pandas_ta as ta
        
        # RSI
        df['rsi'] = ta.rsi(df['Close'], length=rsi_period)
        
        # MACD
        macd = ta.macd(
            df['Close'],
            fast=macd_fast,
            slow=macd_slow,
            signal=macd_signal
        )
        if macd is not None:
            df['macd'] = macd[f'MACD_{macd_fast}_{macd_slow}_{macd_signal}']
            df['macd_signal'] = macd[f'MACDs_{macd_fast}_{macd_slow}_{macd_signal}']
            df['macd_hist'] = macd[f'MACDh_{macd_fast}_{macd_slow}_{macd_signal}']
        
        # Bollinger Bands
        bbands = ta.bbands(df['Close'], length=bb_window, std=bb_std)
        if bbands is not None:
            df['bb_upper'] = bbands[f'BBU_{bb_window}_{bb_std}.0']
            df['bb_middle'] = bbands[f'BBM_{bb_window}_{bb_std}.0']
            df['bb_lower'] = bbands[f'BBL_{bb_window}_{bb_std}.0']
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
            df['bb_position'] = (df['Close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # ATR
        df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=atr_period)
        df['atr_pct'] = df['atr'] / df['Close'] * 100
        
        # Moving Averages
        df['sma_20'] = ta.sma(df['Close'], length=20)
        df['sma_50'] = ta.sma(df['Close'], length=50)
        df['sma_200'] = ta.sma(df['Close'], length=200)
        df['ema_12'] = ta.ema(df['Close'], length=12)
        df['ema_26'] = ta.ema(df['Close'], length=26)
        
        # Price vs Moving Averages
        df['price_vs_sma20'] = df['Close'] / df['sma_20'] - 1
        df['price_vs_sma50'] = df['Close'] / df['sma_50'] - 1
        df['price_vs_sma200'] = df['Close'] / df['sma_200'] - 1
        
        # Volume indicators
        df['volume_sma_20'] = ta.sma(df['Volume'], length=20)
        df['volume_ratio'] = df['Volume'] / df['volume_sma_20']
        
        logger.info(f"Added technical indicators: {len(df.columns)} total columns")
        
    except ImportError:
        logger.warning("pandas_ta not installed, using basic indicators only")
        
        # Fallback to basic indicators
        df['sma_20'] = df['Close'].rolling(window=20).mean()
        df['sma_50'] = df['Close'].rolling(window=50).mean()
        df['sma_200'] = df['Close'].rolling(window=200).mean()
        
        # Basic returns
        df['returns_1d'] = df['Close'].pct_change(1)
        df['returns_5d'] = df['Close'].pct_change(5)
        df['returns_20d'] = df['Close'].pct_change(20)
    
    return df


def add_india_specific_features(
    df: pd.DataFrame,
    fii_data: Optional[pd.DataFrame] = None,
    india_vix: Optional[pd.Series] = None,
    pcr_data: Optional[pd.Series] = None,
    banknifty_data: Optional[pd.DataFrame] = None,
    nifty_data: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Add India-specific features to the dataset.
    
    Args:
        df: DataFrame with stock data
        fii_data: DataFrame with FII/DII net flows
        india_vix: Series with India VIX values
        pcr_data: Series with put-call ratio
        banknifty_data: Bank Nifty index data
        nifty_data: Nifty 50 index data
        
    Returns:
        DataFrame with added features
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    # Add FII/DII features
    if fii_data is not None and not fii_data.empty:
        df = df.join(fii_data[['fii_net', 'dii_net']], how='left')
        
        # FII flow momentum (3-day average)
        df['fii_net_3d_avg'] = df['fii_net'].rolling(window=3).mean()
        df['dii_net_3d_avg'] = df['dii_net'].rolling(window=3).mean()
        
        # FII/DII ratio
        df['fii_dii_ratio'] = df['fii_net'] / (df['dii_net'] + 1e-10)
    
    # Add India VIX
    if india_vix is not None and not india_vix.empty:
        df['india_vix'] = india_vix
        
        # VIX regime
        df['vix_regime'] = pd.cut(
            df['india_vix'],
            bins=[0, 15, 20, 25, 30, float('inf')],
            labels=['low', 'normal', 'elevated', 'high', 'extreme']
        )
        
        # VIX change
        df['vix_change_1d'] = df['india_vix'].pct_change(1)
        df['vix_change_5d'] = df['india_vix'].pct_change(5)
    
    # Add PCR
    if pcr_data is not None and not pcr_data.empty:
        df['pcr'] = pcr_data
        df['pcr_sma_5'] = df['pcr'].rolling(window=5).mean()
    
    # Add BankNifty/Nifty ratio
    if banknifty_data is not None and nifty_data is not None:
        if not banknifty_data.empty and not nifty_data.empty:
            df['banknifty_nifty_ratio'] = (
                banknifty_data['Close'] / nifty_data['Close']
            )
            df['banknifty_nifty_ratio_change'] = df['banknifty_nifty_ratio'].pct_change(5)
    
    # Add market breadth proxy (if Nifty data available)
    if nifty_data is not None and not nifty_data.empty:
        df['nifty_return_1d'] = nifty_data['Close'].pct_change(1)
        df['nifty_return_5d'] = nifty_data['Close'].pct_change(5)
        
        # Stock vs Nifty (relative strength)
        if 'Close' in df.columns:
            df['stock_vs_nifty_5d'] = (
                df['Close'].pct_change(5) - df['nifty_return_5d']
            )
    
    logger.info(f"Added India-specific features: {len(df.columns)} total columns")
    return df


def add_momentum_features(
    df: pd.DataFrame,
    lookback_periods: List[int] = [21, 63, 126, 252]
) -> pd.DataFrame:
    """
    Add momentum features (returns over various periods).
    
    Args:
        df: DataFrame with price data
        lookback_periods: List of periods in trading days
        
    Returns:
        DataFrame with momentum features
    """
    if df.empty or 'Close' not in df.columns:
        return df
    
    df = df.copy()
    
    for period in lookback_periods:
        df[f'returns_{period}d'] = df['Close'].pct_change(period)
        
        # Also add log returns
        df[f'log_returns_{period}d'] = np.log(df['Close'] / df['Close'].shift(period))
    
    # 12-1 momentum (12-month minus 1-month)
    if 252 in lookback_periods and 21 in lookback_periods:
        df['momentum_12_1'] = df['returns_252d'] - df['returns_21d']
    
    logger.info(f"Added momentum features for periods: {lookback_periods}")
    return df


def add_volatility_features(
    df: pd.DataFrame,
    windows: List[int] = [5, 10, 20, 60]
) -> pd.DataFrame:
    """
    Add volatility features.
    
    Args:
        df: DataFrame with price data
        windows: List of lookback windows
        
    Returns:
        DataFrame with volatility features
    """
    if df.empty or 'Close' not in df.columns:
        return df
    
    df = df.copy()
    
    # Daily returns
    df['returns_1d'] = df['Close'].pct_change(1)
    
    for window in windows:
        # Realized volatility (annualized)
        df[f'volatility_{window}d'] = (
            df['returns_1d'].rolling(window=window).std() * np.sqrt(252)
        )
        
        # EWMA volatility
        df[f'volatility_ewma_{window}d'] = (
            df['returns_1d'].ewm(span=window).std() * np.sqrt(252)
        )
    
    logger.info(f"Added volatility features for windows: {windows}")
    return df


def create_feature_matrix(
    price_dict: dict,
    add_technicals: bool = True,
    add_india_features: bool = True,
    add_momentum: bool = True,
    add_volatility: bool = True
) -> pd.DataFrame:
    """
    Create a feature matrix from multiple price series.
    
    Args:
        price_dict: Dictionary mapping ticker to OHLCV DataFrame
        add_technicals: Whether to add technical indicators
        add_india_features: Whether to add India-specific features
        add_momentum: Whether to add momentum features
        add_volatility: Whether to add volatility features
        
    Returns:
        Combined feature matrix
    """
    all_features = []
    
    for ticker, df in price_dict.items():
        if df.empty:
            continue
        
        features = df.copy()
        
        if add_technicals:
            features = add_technical_indicators(features)
        
        if add_momentum:
            features = add_momentum_features(features)
        
        if add_volatility:
            features = add_volatility_features(features)
        
        # Prefix columns with ticker name
        features = features.rename(columns=lambda x: f"{ticker}_{x}")
        all_features.append(features)
    
    if not all_features:
        return pd.DataFrame()
    
    # Join all features on date index
    combined = all_features[0]
    for feat in all_features[1:]:
        combined = combined.join(feat, how='outer')
    
    return combined.dropna(how='all')


if __name__ == "__main__":
    # Test the module
    logging.basicConfig(level=logging.INFO)
    
    # Create sample OHLCV data
    dates = pd.date_range("2024-01-01", periods=100, freq='D')
    np.random.seed(42)
    
    sample_data = pd.DataFrame({
        'Open': 100 + np.random.randn(100).cumsum(),
        'High': 102 + np.random.randn(100).cumsum(),
        'Low': 98 + np.random.randn(100).cumsum(),
        'Close': 100 + np.random.randn(100).cumsum(),
        'Volume': np.random.randint(10000, 100000, 100)
    }, index=dates)
    
    print("=== Add technical indicators ===")
    data_with_indicators = add_technical_indicators(sample_data)
    print(data_with_indicators.tail())
    print(f"Columns: {list(data_with_indicators.columns)}")
    
    print("\n=== Add momentum features ===")
    data_with_momentum = add_momentum_features(sample_data)
    print(data_with_momentum[['Close', 'returns_21d', 'returns_252d', 'momentum_12_1']].tail())
    
    print("\n=== Add volatility features ===")
    data_with_vol = add_volatility_features(sample_data)
    print(data_with_vol[['Close', 'volatility_20d', 'volatility_60d']].tail())
