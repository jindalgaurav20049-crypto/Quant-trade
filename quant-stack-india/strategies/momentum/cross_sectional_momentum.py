"""
Cross-Sectional Momentum Strategy

Ranks stocks by their momentum and goes long the top performers
and optionally short the bottom performers.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class CrossSectionalMomentum(BaseStrategy):
    """
    Cross-sectional momentum strategy.
    
    Goes long top N stocks by momentum, optionally shorts bottom N.
    """
    
    def __init__(
        self,
        lookback_days: int = 252,
        top_n: int = 10,
        bottom_n: int = 0,
        weighting: str = "equal",  # "equal" or "momentum_weighted"
        name: str = "CrossSectionalMomentum"
    ):
        super().__init__(name=name)
        self.lookback_days = lookback_days
        self.top_n = top_n
        self.bottom_n = bottom_n
        self.weighting = weighting
        
        self.parameters = {
            "lookback_days": lookback_days,
            "top_n": top_n,
            "bottom_n": bottom_n,
            "weighting": weighting,
        }
    
    def compute_momentum(self, prices: pd.DataFrame) -> pd.Series:
        """
        Compute momentum scores for all stocks.
        
        Args:
            prices: DataFrame with dates as index, tickers as columns
            
        Returns:
            Series of momentum scores
        """
        if len(prices) < self.lookback_days:
            logger.warning(f"Insufficient data: {len(prices)} < {self.lookback_days}")
            return pd.Series(dtype=float)
        
        # Calculate returns over lookback period
        start_prices = prices.iloc[-self.lookback_days]
        end_prices = prices.iloc[-1]
        
        momentum = (end_prices / start_prices) - 1.0
        return momentum.dropna()
    
    def select_stocks(self, momentum: pd.Series) -> Tuple[List[str], List[str]]:
        """
        Select top and bottom stocks by momentum.
        
        Args:
            momentum: Series of momentum scores
            
        Returns:
            Tuple of (long_tickers, short_tickers)
        """
        if momentum.empty:
            return [], []
        
        # Sort by momentum
        sorted_momentum = momentum.sort_values(ascending=False)
        
        # Select top N
        long_tickers = sorted_momentum.head(self.top_n).index.tolist()
        
        # Select bottom N (for shorting)
        short_tickers = []
        if self.bottom_n > 0:
            short_tickers = sorted_momentum.tail(self.bottom_n).index.tolist()
        
        logger.info(f"Selected {len(long_tickers)} long, {len(short_tickers)} short")
        return long_tickers, short_tickers
    
    def compute_weights(
        self,
        long_tickers: List[str],
        short_tickers: List[str],
        momentum: pd.Series
    ) -> Dict[str, float]:
        """
        Compute portfolio weights.
        
        Args:
            long_tickers: List of long positions
            short_tickers: List of short positions
            momentum: Momentum scores for weighting
            
        Returns:
            Dictionary of ticker to weight
        """
        weights = {}
        
        if not long_tickers:
            return weights
        
        if self.weighting == "equal":
            # Equal weight
            long_weight = 1.0 / len(long_tickers)
            for ticker in long_tickers:
                weights[ticker] = long_weight
        
        elif self.weighting == "momentum_weighted":
            # Weight by momentum score
            long_momentum = momentum[long_tickers].abs()
            total_momentum = long_momentum.sum()
            
            if total_momentum > 0:
                for ticker in long_tickers:
                    weights[ticker] = abs(momentum[ticker]) / total_momentum
        
        # Add short positions (negative weights)
        if short_tickers:
            if self.weighting == "equal":
                short_weight = -1.0 / len(short_tickers)
                for ticker in short_tickers:
                    weights[ticker] = short_weight
            
            elif self.weighting == "momentum_weighted":
                short_momentum = momentum[short_tickers].abs()
                total_momentum = short_momentum.sum()
                
                if total_momentum > 0:
                    for ticker in short_tickers:
                        weights[ticker] = -abs(momentum[ticker]) / total_momentum
        
        return weights
    
    def generate_signals(
        self,
        prices: pd.DataFrame,
        **kwargs
    ) -> Dict[str, float]:
        """
        Generate trading signals.
        
        Args:
            prices: DataFrame with price data
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of ticker to target weight
        """
        if not self.validate_data(prices):
            return {}
        
        momentum = self.compute_momentum(prices)
        if momentum.empty:
            logger.warning("No momentum scores computed")
            return {}
        
        long_tickers, short_tickers = self.select_stocks(momentum)
        weights = self.compute_weights(long_tickers, short_tickers, momentum)
        
        return weights
