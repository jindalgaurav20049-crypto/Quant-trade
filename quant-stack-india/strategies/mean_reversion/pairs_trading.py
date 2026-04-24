"""
Pairs Trading Strategy

Statistical arbitrage using cointegrated pairs.
Uses Engle-Granger cointegration test and Kalman filter for hedge ratio.

Hardcoded pairs for Indian markets:
- HDFCBANK / ICICIBANK (banking)
- TCS / INFY (IT services)
- BAJFINANCE / KOTAKBANK (financial services)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

# Predefined pairs for Indian markets
DEFAULT_PAIRS = [
    ("HDFCBANK.NS", "ICICIBANK.NS"),
    ("TCS.NS", "INFY.NS"),
    ("BAJFINANCE.NS", "KOTAKBANK.NS"),
]


class PairsTrading(BaseStrategy):
    """
    Pairs trading strategy using cointegration.
    """
    
    def __init__(
        self,
        pairs: Optional[List[Tuple[str, str]]] = None,
        lookback: int = 252,
        entry_zscore: float = 2.0,
        exit_zscore: float = 0.5,
        use_kalman: bool = True,
        name: str = "PairsTrading"
    ):
        super().__init__(name=name)
        self.pairs = pairs or DEFAULT_PAIRS
        self.lookback = lookback
        self.entry_zscore = entry_zscore
        self.exit_zscore = exit_zscore
        self.use_kalman = use_kalman
        
        self.parameters = {
            "pairs": self.pairs,
            "lookback": lookback,
            "entry_zscore": entry_zscore,
            "exit_zscore": exit_zscore,
            "use_kalman": use_kalman,
        }
    
    def test_cointegration(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series
    ) -> Tuple[bool, float]:
        """
        Test if two price series are cointegrated using Engle-Granger.
        
        Args:
            prices_a: Price series for stock A
            prices_b: Price series for stock B
            
        Returns:
            Tuple of (is_cointegrated, p_value)
        """
        try:
            from statsmodels.tsa.stattools import coint
            
            # Align series
            common_index = prices_a.index.intersection(prices_b.index)
            a = prices_a.loc[common_index].dropna()
            b = prices_b.loc[common_index].dropna()
            
            if len(a) < 30 or len(b) < 30:
                return False, 1.0
            
            score, p_value, _ = coint(a, b)
            
            # p < 0.05 indicates cointegration
            is_cointegrated = p_value < 0.05
            
            return is_cointegrated, p_value
            
        except Exception as e:
            logger.error(f"Cointegration test failed: {e}")
            return False, 1.0
    
    def compute_hedge_ratio_ols(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series
    ) -> float:
        """
        Compute hedge ratio using OLS regression.
        
        Args:
            prices_a: Price series for stock A
            prices_b: Price series for stock B
            
        Returns:
            Hedge ratio (beta)
        """
        try:
            from statsmodels.regression.linear_model import OLS
            from statsmodels.tools import add_constant
            
            # Align series
            common_index = prices_a.index.intersection(prices_b.index)
            a = prices_a.loc[common_index].dropna()
            b = prices_b.loc[common_index].dropna()
            
            if len(a) < 30:
                return 1.0
            
            # OLS: A = alpha + beta * B
            X = add_constant(b)
            model = OLS(a, X).fit()
            
            return model.params[1]  # beta coefficient
            
        except Exception as e:
            logger.error(f"OLS hedge ratio failed: {e}")
            return 1.0
    
    def compute_hedge_ratio_kalman(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series
    ) -> float:
        """
        Compute dynamic hedge ratio using Kalman filter.
        
        Args:
            prices_a: Price series for stock A
            prices_b: Price series for stock B
            
        Returns:
            Latest hedge ratio
        """
        try:
            from pykalman import KalmanFilter
            
            # Align series
            common_index = prices_a.index.intersection(prices_b.index)
            a = prices_a.loc[common_index].dropna().values
            b = prices_b.loc[common_index].dropna().values
            
            if len(a) < 30:
                return 1.0
            
            # Kalman filter for dynamic beta
            kf = KalmanFilter(
                n_dim_obs=1,
                n_dim_state=1,
                initial_state_mean=1.0,
                initial_state_covariance=1.0,
                observation_matrices=b.reshape(-1, 1, 1),
                observation_covariance=1.0,
                transition_covariance=0.01
            )
            
            state_means, _ = kf.filter(a)
            
            return float(state_means[-1, 0])
            
        except Exception as e:
            logger.error(f"Kalman filter failed: {e}")
            return self.compute_hedge_ratio_ols(prices_a, prices_b)
    
    def compute_spread(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series,
        hedge_ratio: float
    ) -> pd.Series:
        """
        Compute the spread between two price series.
        
        Args:
            prices_a: Price series for stock A
            prices_b: Price series for stock B
            hedge_ratio: Hedge ratio
            
        Returns:
            Spread series
        """
        common_index = prices_a.index.intersection(prices_b.index)
        a = prices_a.loc[common_index]
        b = prices_b.loc[common_index]
        
        spread = a - hedge_ratio * b
        return spread
    
    def compute_zscore(self, spread: pd.Series) -> pd.Series:
        """
        Compute z-score of the spread.
        
        Args:
            spread: Spread series
            
        Returns:
            Z-score series
        """
        mean = spread.mean()
        std = spread.std()
        
        if std == 0:
            return pd.Series(0, index=spread.index)
        
        return (spread - mean) / std
    
    def generate_pair_signal(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series
    ) -> Dict:
        """
        Generate trading signal for a pair.
        
        Args:
            prices_a: Price series for stock A
            prices_b: Price series for stock B
            
        Returns:
            Signal dictionary
        """
        # Use recent data for lookback
        a_recent = prices_a.tail(self.lookback)
        b_recent = prices_b.tail(self.lookback)
        
        # Test cointegration
        is_coint, p_value = self.test_cointegration(a_recent, b_recent)
        
        if not is_coint:
            return {
                'pair': (prices_a.name, prices_b.name),
                'signal': 0,
                'is_cointegrated': False,
                'p_value': p_value,
            }
        
        # Compute hedge ratio
        if self.use_kalman:
            hedge_ratio = self.compute_hedge_ratio_kalman(a_recent, b_recent)
        else:
            hedge_ratio = self.compute_hedge_ratio_ols(a_recent, b_recent)
        
        # Compute spread and z-score
        spread = self.compute_spread(prices_a, prices_b, hedge_ratio)
        zscore = self.compute_zscore(spread.tail(self.lookback))
        current_z = zscore.iloc[-1]
        
        # Generate signal
        signal = 0
        if current_z > self.entry_zscore:
            signal = -1  # Spread will narrow (short A, long B)
        elif current_z < -self.entry_zscore:
            signal = 1  # Spread will widen (long A, short B)
        elif abs(current_z) < self.exit_zscore:
            signal = 0  # Exit position
        
        return {
            'pair': (prices_a.name, prices_b.name),
            'signal': signal,
            'zscore': current_z,
            'hedge_ratio': hedge_ratio,
            'is_cointegrated': True,
            'p_value': p_value,
        }
    
    def generate_signals(
        self,
        prices: pd.DataFrame,
        **kwargs
    ) -> Dict[str, float]:
        """
        Generate trading signals for all pairs.
        
        Args:
            prices: DataFrame with price data (dates x tickers)
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of ticker to weight
        """
        if not self.validate_data(prices):
            return {}
        
        weights = {}
        
        for stock_a, stock_b in self.pairs:
            if stock_a not in prices.columns or stock_b not in prices.columns:
                logger.warning(f"Pair ({stock_a}, {stock_b}) not in price data")
                continue
            
            result = self.generate_pair_signal(
                prices[stock_a],
                prices[stock_b]
            )
            
            signal = result['signal']
            hedge_ratio = result.get('hedge_ratio', 1.0)
            
            if signal != 0:
                # Normalize weights within pair
                total = 1.0 + abs(hedge_ratio)
                weights[stock_a] = signal / total
                weights[stock_b] = -signal * hedge_ratio / total
        
        logger.info(f"Generated pair signals: {len(weights)} positions")
        return weights
    
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
        return signals
