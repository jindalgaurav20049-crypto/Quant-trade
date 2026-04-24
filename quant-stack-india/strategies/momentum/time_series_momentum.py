"""
Time Series Momentum Strategy

Generates buy/sell signals based on a stock's own past performance.
Also known as trend-following at the individual stock level.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class TimeSeriesMomentum(BaseStrategy):
    """
    Time series momentum (trend-following) strategy.
    
    Goes long when price is above moving average, short when below.
    """
    
    def __init__(
        self,
        lookback_days: int = 252,
        short_ma: int = 50,
        long_ma: int = 200,
        name: str = "TimeSeriesMomentum"
    ):
        super().__init__(name=name)
        self.lookback_days = lookback_days
        self.short_ma = short_ma
        self.long_ma = long_ma
        
        self.parameters = {
            "lookback_days": lookback_days,
            "short_ma": short_ma,
            "long_ma": long_ma,
        }
    
    def compute_signal(self, prices: pd.Series) -> float:
        """
        Compute momentum signal for a single stock.
        
        Args:
            prices: Series of prices
            
        Returns:
            Signal value (-1 to 1)
        """
        if len(prices) < self.long_ma:
            return 0.0
        
        # Calculate moving averages
        short_ma = prices.rolling(window=self.short_ma).mean().iloc[-1]
        long_ma = prices.rolling(window=self.long_ma).mean().iloc[-1]
        current_price = prices.iloc[-1]
        
        # Golden cross / death cross logic
        if short_ma > long_ma and current_price > short_ma:
            return 1.0  # Strong bullish
        elif short_ma > long_ma:
            return 0.5  # Moderate bullish
        elif short_ma < long_ma and current_price < short_ma:
            return -1.0  # Strong bearish
        elif short_ma < long_ma:
            return -0.5  # Moderate bearish
        
        return 0.0
    
    def generate_signals(
        self,
        prices: pd.DataFrame,
        **kwargs
    ) -> Dict[str, float]:
        """
        Generate trading signals for all stocks.
        
        Args:
            prices: DataFrame with price data (dates x tickers)
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of ticker to signal strength
        """
        if not self.validate_data(prices):
            return {}
        
        signals = {}
        
        for ticker in prices.columns:
            price_series = prices[ticker].dropna()
            
            if len(price_series) < self.long_ma:
                continue
            
            signal = self.compute_signal(price_series)
            
            if signal != 0:
                signals[ticker] = signal
        
        logger.info(f"Generated signals for {len(signals)} stocks")
        return signals
    
    def compute_weights(
        self,
        signals: Dict[str, float],
        **kwargs
    ) -> Dict[str, float]:
        """
        Convert signals to portfolio weights.
        
        Args:
            signals: Dictionary of signals
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of ticker to weight
        """
        if not signals:
            return {}
        
        # Normalize signals to sum to 1
        total_signal = sum(abs(s) for s in signals.values())
        
        if total_signal == 0:
            return {}
        
        weights = {
            ticker: signal / total_signal
            for ticker, signal in signals.items()
        }
        
        return weights
