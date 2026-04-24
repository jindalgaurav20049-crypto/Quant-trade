"""
Hyperparameter Search

Optuna-based hyperparameter optimization for strategies.
"""

import logging
from typing import Dict, Any, Callable
import pandas as pd

logger = logging.getLogger(__name__)


class HyperparameterSearch:
    """
    Hyperparameter optimization using Optuna.
    """
    
    def __init__(self, n_trials: int = 100, direction: str = "maximize"):
        """
        Initialize search.
        
        Args:
            n_trials: Number of optimization trials
            direction: "maximize" or "minimize"
        """
        self.n_trials = n_trials
        self.direction = direction
    
    def search(
        self,
        strategy_class: type,
        prices: pd.DataFrame,
        param_space: Dict[str, Any],
        metric_fn: Callable
    ) -> Dict[str, Any]:
        """
        Run hyperparameter search.
        
        Args:
            strategy_class: Strategy class to optimize
            prices: Price data
            param_space: Parameter search space
            metric_fn: Function to compute metric from strategy results
            
        Returns:
            Best parameters
        """
        try:
            import optuna
        except ImportError:
            logger.error("optuna not installed")
            return {}
        
        def objective(trial):
            # Build parameters from search space
            params = {}
            for param_name, param_config in param_space.items():
                param_type = param_config['type']
                
                if param_type == 'int':
                    params[param_name] = trial.suggest_int(
                        param_name,
                        param_config['low'],
                        param_config['high']
                    )
                elif param_type == 'float':
                    params[param_name] = trial.suggest_float(
                        param_name,
                        param_config['low'],
                        param_config['high'],
                        log=param_config.get('log', False)
                    )
                elif param_type == 'categorical':
                    params[param_name] = trial.suggest_categorical(
                        param_name,
                        param_config['choices']
                    )
            
            # Create strategy and evaluate
            try:
                strategy = strategy_class(**params)
                result = metric_fn(strategy, prices)
                return result
            except Exception as e:
                logger.warning(f"Trial failed: {e}")
                return float('-inf') if self.direction == "maximize" else float('inf')
        
        # Create study
        study = optuna.create_study(direction=self.direction)
        study.optimize(objective, n_trials=self.n_trials)
        
        logger.info(f"Best params: {study.best_params}")
        logger.info(f"Best value: {study.best_value}")
        
        return study.best_params


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test HyperparameterSearch ===")
    
    # Create sample data
    import numpy as np
    dates = pd.date_range("2023-01-01", periods=252, freq='D')
    prices = pd.DataFrame({
        'RELIANCE.NS': 100 * (1 + np.random.randn(252).cumsum() * 0.01),
        'TCS.NS': 100 * (1 + np.random.randn(252).cumsum() * 0.01),
    }, index=dates)
    
    # Define simple metric function
    def simple_metric(strategy, prices):
        returns = prices.pct_change().mean().mean()
        return returns
    
    # Define simple strategy class
    class SimpleStrategy:
        def __init__(self, lookback=20):
            self.lookback = lookback
    
    search = HyperparameterSearch(n_trials=10)
    
    best_params = search.search(
        SimpleStrategy,
        prices,
        param_space={
            'lookback': {'type': 'int', 'low': 5, 'high': 50}
        },
        metric_fn=simple_metric
    )
    
    print(f"Best params: {best_params}")
