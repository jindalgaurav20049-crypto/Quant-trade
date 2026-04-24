"""
VectorBT Backtesting Engine

Complete vectorbt backtesting engine for Indian strategies.
"""

import logging
from typing import Dict
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def run_momentum_backtest(
    prices: pd.DataFrame,
    top_n: int = 10,
    lookback: int = 252
) -> Dict:
    """
    Run momentum backtest using vectorbt.
    
    Args:
        prices: DataFrame with price data
        top_n: Number of top stocks to select
        lookback: Lookback period for momentum calculation
        
    Returns:
        Dictionary with backtest results
    """
    try:
        import vectorbt as vbt
    except ImportError:
        logger.error("vectorbt not installed")
        return {}
    
    if prices.empty:
        logger.error("Empty price DataFrame")
        return {}
    
    try:
        # Calculate momentum
        momentum = prices.pct_change(lookback)
        
        # Rank stocks by momentum
        rankings = momentum.rank(axis=1, ascending=False)
        
        # Create signals for top N stocks
        signals = (rankings <= top_n).astype(int)
        
        # Equal weight within top N
        weights = signals.div(signals.sum(axis=1), axis=0).fillna(0)
        
        # Run backtest
        portfolio = vbt.Portfolio.from_orders(
            prices,
            weights,
            init_cash=1_000_000,
            fees=0.001,  # 0.1% transaction cost
            slippage=0.001,
        )
        
        return {
            'total_return': portfolio.total_return(),
            'sharpe': portfolio.sharpe_ratio(),
            'max_drawdown': portfolio.max_drawdown(),
            'portfolio': portfolio,
        }
        
    except Exception as e:
        logger.error(f"Momentum backtest failed: {e}")
        return {}


def run_bollinger_backtest(
    prices: pd.DataFrame,
    window: int = 20,
    std: float = 2.0
) -> Dict:
    """
    Run Bollinger Bands mean reversion backtest.
    
    Args:
        prices: DataFrame with price data
        window: Bollinger Bands window
        std: Number of standard deviations
        
    Returns:
        Dictionary with backtest results
    """
    try:
        import vectorbt as vbt
    except ImportError:
        logger.error("vectorbt not installed")
        return {}
    
    if prices.empty:
        logger.error("Empty price DataFrame")
        return {}
    
    try:
        # Calculate Bollinger Bands
        sma = prices.rolling(window=window).mean()
        std_dev = prices.rolling(window=window).std()
        upper = sma + std * std_dev
        lower = sma - std * std_dev
        
        # Entry: price crosses below lower band
        entries = prices < lower
        
        # Exit: price crosses above middle band
        exits = prices > sma
        
        # Run backtest
        portfolio = vbt.Portfolio.from_signals(
            prices,
            entries,
            exits,
            init_cash=1_000_000,
            fees=0.001,
            slippage=0.001,
        )
        
        return {
            'total_return': portfolio.total_return(),
            'sharpe': portfolio.sharpe_ratio(),
            'max_drawdown': portfolio.max_drawdown(),
            'portfolio': portfolio,
        }
        
    except Exception as e:
        logger.error(f"Bollinger backtest failed: {e}")
        return {}


def compare_strategies(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Compare all strategies and return summary.
    
    Args:
        prices: DataFrame with price data
        
    Returns:
        Summary DataFrame
    """
    results = []
    
    # Momentum
    momentum_result = run_momentum_backtest(prices)
    if momentum_result:
        results.append({
            'Strategy': 'Momentum',
            'Return': momentum_result['total_return'],
            'Sharpe': momentum_result['sharpe'],
            'MaxDD': momentum_result['max_drawdown'],
        })
    
    # Bollinger
    bollinger_result = run_bollinger_backtest(prices)
    if bollinger_result:
        results.append({
            'Strategy': 'Bollinger',
            'Return': bollinger_result['total_return'],
            'Sharpe': bollinger_result['sharpe'],
            'MaxDD': bollinger_result['max_drawdown'],
        })
    
    # Buy and Hold (Nifty 50 proxy)
    if not prices.empty:
        nifty_returns = prices.mean(axis=1).pct_change().dropna()
        total_return = (1 + nifty_returns).prod() - 1
        sharpe = nifty_returns.mean() / nifty_returns.std() * np.sqrt(252)
        cumulative = (1 + nifty_returns).cumprod()
        max_dd = (cumulative / cumulative.cummax() - 1).min()
        
        results.append({
            'Strategy': 'Buy & Hold',
            'Return': total_return,
            'Sharpe': sharpe,
            'MaxDD': max_dd,
        })
    
    return pd.DataFrame(results)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test VectorBT Engine ===")
    
    # Create sample data
    dates = pd.date_range("2023-01-01", periods=252, freq='D')
    sample_prices = pd.DataFrame({
        'RELIANCE.NS': 100 * (1 + np.random.randn(252).cumsum() * 0.01),
        'TCS.NS': 100 * (1 + np.random.randn(252).cumsum() * 0.01),
        'HDFCBANK.NS': 100 * (1 + np.random.randn(252).cumsum() * 0.01),
    }, index=dates)
    
    print("\n=== Momentum Backtest ===")
    result = run_momentum_backtest(sample_prices)
    print(result)
    
    print("\n=== Strategy Comparison ===")
    comparison = compare_strategies(sample_prices)
    print(comparison)
