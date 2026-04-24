"""
Walk-Forward Optimization

Implements walk-forward optimization with in-sample/out-of-sample splits.
"""

import logging
from typing import Dict, List, Callable, Any
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class WalkForwardOptimizer:
    """
    Walk-forward optimization with IS/OOS split.
    """
    
    def __init__(self, n_splits: int = 5, is_pct: float = 0.7):
        """
        Initialize walk-forward optimizer.
        
        Args:
            n_splits: Number of walk-forward splits
            is_pct: Percentage of data for in-sample training
        """
        self.n_splits = n_splits
        self.is_pct = is_pct
        self.results = []
    
    def create_splits(self, prices: pd.DataFrame) -> List[tuple]:
        """
        Create walk-forward splits.
        
        Args:
            prices: Price DataFrame
            
        Returns:
            List of (is_start, is_end, oos_start, oos_end) tuples
        """
        n = len(prices)
        split_size = n // self.n_splits
        
        splits = []
        for i in range(self.n_splits):
            start = i * split_size
            end = start + split_size
            
            is_end = start + int(split_size * self.is_pct)
            
            splits.append((
                start,
                is_end,
                is_end,
                end
            ))
        
        return splits
    
    def run(
        self,
        prices: pd.DataFrame,
        strategy_fn: Callable,
        param_grid: Dict[str, List[Any]]
    ) -> Dict:
        """
        Run walk-forward optimization.
        
        Args:
            prices: Price DataFrame
            strategy_fn: Strategy function
            param_grid: Parameter grid to search
            
        Returns:
            Results dictionary
        """
        splits = self.create_splits(prices)
        
        is_sharpes = []
        oos_sharpes = []
        
        for i, (is_start, is_end, oos_start, oos_end) in enumerate(splits):
            logger.info(f"Running split {i+1}/{self.n_splits}")
            
            # In-sample data
            is_data = prices.iloc[is_start:is_end]
            
            # Out-of-sample data
            oos_data = prices.iloc[oos_start:oos_end]
            
            # Optimize on in-sample
            best_params = self._optimize(is_data, strategy_fn, param_grid)
            
            # Evaluate on both
            is_sharpe = self._evaluate(is_data, strategy_fn, best_params)
            oos_sharpe = self._evaluate(oos_data, strategy_fn, best_params)
            
            is_sharpes.append(is_sharpe)
            oos_sharpes.append(oos_sharpe)
            
            self.results.append({
                'split': i + 1,
                'best_params': best_params,
                'is_sharpe': is_sharpe,
                'oos_sharpe': oos_sharpe,
            })
        
        return {
            'is_sharpes': is_sharpes,
            'oos_sharpes': oos_sharpes,
            'degradation_ratio': np.mean(oos_sharpes) / np.mean(is_sharpes) if np.mean(is_sharpes) > 0 else 0,
            'results': self.results,
        }
    
    def _optimize(
        self,
        data: pd.DataFrame,
        strategy_fn: Callable,
        param_grid: Dict[str, List[Any]]
    ) -> Dict:
        """Simple grid search optimization."""
        from itertools import product
        
        best_sharpe = -np.inf
        best_params = {}
        
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        
        for combo in product(*values):
            params = dict(zip(keys, combo))
            sharpe = self._evaluate(data, strategy_fn, params)
            
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_params = params
        
        return best_params
    
    def _evaluate(
        self,
        data: pd.DataFrame,
        strategy_fn: Callable,
        params: Dict
    ) -> float:
        """Evaluate strategy with given parameters."""
        try:
            result = strategy_fn(data, **params)
            return result.get('sharpe', 0)
        except Exception as e:
            logger.warning(f"Evaluation failed: {e}")
            return 0
    
    def compute_degradation_ratio(self) -> float:
        """
        Compute IS/OOS degradation ratio.
        Healthy if > 0.5.
        
        Returns:
            Degradation ratio
        """
        if not self.results:
            return 0
        
        is_sharpes = [r['is_sharpe'] for r in self.results]
        oos_sharpes = [r['oos_sharpe'] for r in self.results]
        
        mean_is = np.mean(is_sharpes)
        mean_oos = np.mean(oos_sharpes)
        
        return mean_oos / mean_is if mean_is > 0 else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test WalkForwardOptimizer ===")
    
    # Create sample data
    dates = pd.date_range("2020-01-01", periods=1000, freq='D')
    sample_prices = pd.DataFrame({
        'RELIANCE.NS': 100 * (1 + np.random.randn(1000).cumsum() * 0.01),
        'TCS.NS': 100 * (1 + np.random.randn(1000).cumsum() * 0.01),
    }, index=dates)
    
    # Define simple strategy function
    def simple_momentum(data, lookback=252):
        returns = data.pct_change(lookback).iloc[-1]
        return {'sharpe': returns.mean() / returns.std() if returns.std() > 0 else 0}
    
    optimizer = WalkForwardOptimizer(n_splits=3)
    
    results = optimizer.run(
        sample_prices,
        simple_momentum,
        param_grid={'lookback': [126, 252]}
    )
    
    print(f"Degradation ratio: {results['degradation_ratio']:.2f}")
