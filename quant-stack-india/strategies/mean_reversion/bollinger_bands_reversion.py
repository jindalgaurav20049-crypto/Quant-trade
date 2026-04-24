"""
Bollinger Bands Mean Reversion Strategy

Buys when price touches lower band, sells when price touches upper band.
Exits when price returns to middle band.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class BollingerBandsReversion(BaseStrategy):
    """
    Bollinger Bands mean reversion strategy.
    
    Entry: Price crosses below lower band (buy signal)
    Exit: Price crosses above middle band
    """
    
    def __init__(
        self,
        window: int = 20,
        num_std: float = 2.0,
        exit_at_middle: bool = True,
        name: str = "BollingerBandsReversion"
    ):
        super().__init__(name=name)
        self.window = window
        self.num_std = num_std
        self.exit_at_middle = exit_at_middle
        
        self.parameters = {
            "window": window,
            "num_std": num_std,
            "exit_at_middle": exit_at_middle,
        }
    
    def compute_bollinger_bands(
        self,
        prices: pd.Series
    ) -> pd.DataFrame:
        """
        Compute Bollinger Bands for a price series.
        
        Args:
            prices: Price series
            
        Returns:
            DataFrame with upper, middle, lower bands
        """
        middle = prices.rolling(window=self.window).mean()
        std = prices.rolling(window=self.window).std()
        
        upper = middle + self.num_std * std
        lower = middle - self.num_std * std
        
        return pd.DataFrame({
            'upper': upper,
            'middle': middle,
            'lower': lower,
        })
    
    def generate_signal(self, prices: pd.Series) -> float:
        """
        Generate signal for a single stock.
        
        Args:
            prices: Price series
            
        Returns:
            Signal value (-1, 0, 1)
        """
        if len(prices) < self.window:
            return 0.0
        
        bb = self.compute_bollinger_bands(prices)
        current_price = prices.iloc[-1]
        current_upper = bb['upper'].iloc[-1]
        current_lower = bb['lower'].iloc[-1]
        current_middle = bb['middle'].iloc[-1]
        
        prev_price = prices.iloc[-2] if len(prices) > 1 else current_price
        
        # Buy signal: price crosses below lower band
        if current_price < current_lower and prev_price >= bb['lower'].iloc[-2]:
            return 1.0
        
        # Sell signal: price crosses above upper band
        if current_price > current_upper and prev_price <= bb['upper'].iloc[-2]:
            return -1.0
        
        # Exit long: price crosses above middle band
        if self.exit_at_middle:
            if current_price > current_middle and prev_price <= bb['middle'].iloc[-2]:
                return 0.0
        
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
            
            if len(price_series) < self.window:
                continue
            
            signal = self.generate_signal(price_series)
            
            if signal != 0:
                signals[ticker] = signal
        
        logger.info(f"Generated Bollinger signals for {len(signals)} stocks")
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
        
        # Equal weight for all signals
        n_signals = len(signals)
        weight_per_signal = 1.0 / n_signals if n_signals > 0 else 0
        
        weights = {
            ticker: np.sign(signal) * weight_per_signal
            for ticker, signal in signals.items()
        }
        
        return weights
