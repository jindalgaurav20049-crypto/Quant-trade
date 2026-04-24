"""
Risk Parity Optimizer

Equal risk contribution portfolio using scipy.optimize.
"""

import logging
from typing import Dict
import pandas as pd
import numpy as np
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


class RiskParityOptimizer:
    """
    Risk parity portfolio optimizer.
    
    Allocates capital so that each asset contributes equally to portfolio risk.
    """
    
    def __init__(self):
        """Initialize optimizer."""
        pass
    
    def _portfolio_risk(self, weights: np.ndarray, cov_matrix: np.ndarray) -> float:
        """Calculate portfolio risk (volatility)."""
        return np.sqrt(weights @ cov_matrix @ weights)
    
    def _risk_contribution(self, weights: np.ndarray, cov_matrix: np.ndarray) -> np.ndarray:
        """Calculate risk contribution of each asset."""
        portfolio_vol = self._portfolio_risk(weights, cov_matrix)
        marginal_risk = cov_matrix @ weights
        risk_contrib = weights * marginal_risk / portfolio_vol
        return risk_contrib
    
    def _risk_parity_objective(
        self,
        weights: np.ndarray,
        cov_matrix: np.ndarray,
        target_risk: np.ndarray
    ) -> float:
        """
        Objective function for risk parity optimization.
        Minimizes squared difference between actual and target risk contributions.
        """
        actual_risk = self._risk_contribution(weights, cov_matrix)
        return np.sum((actual_risk - target_risk) ** 2)
    
    def optimize(
        self,
        returns: pd.DataFrame,
        cov_matrix: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """
        Optimize for risk parity.
        
        Args:
            returns: Returns DataFrame
            cov_matrix: Optional covariance matrix
            
        Returns:
            Dictionary of optimal weights
        """
        try:
            if cov_matrix is None:
                cov_matrix = returns.cov() * 252  # Annualized
            
            n = len(returns.columns)
            
            # Initial guess: equal weight
            x0 = np.ones(n) / n
            
            # Target: equal risk contribution
            target_risk = np.ones(n) / n
            
            # Constraints: weights sum to 1
            constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
            
            # Bounds: 0 <= weight <= 1
            bounds = [(0, 1) for _ in range(n)]
            
            # Optimize
            result = minimize(
                self._risk_parity_objective,
                x0,
                args=(cov_matrix.values, target_risk),
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )
            
            if result.success:
                weights = result.x
                return dict(zip(returns.columns, weights))
            else:
                logger.warning("Risk parity optimization failed, using equal weight")
                return {col: 1.0 / n for col in returns.columns}
                
        except Exception as e:
            logger.error(f"Risk parity optimization failed: {e}")
            n = len(returns.columns)
            return {col: 1.0 / n for col in returns.columns}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test RiskParityOptimizer ===")
    
    # Create sample returns
    dates = pd.date_range("2023-01-01", periods=252, freq='D')
    returns = pd.DataFrame({
        'RELIANCE.NS': np.random.randn(252) * 0.02,
        'TCS.NS': np.random.randn(252) * 0.018,
        'HDFCBANK.NS': np.random.randn(252) * 0.015,
    }, index=dates)
    
    optimizer = RiskParityOptimizer()
    weights = optimizer.optimize(returns)
    
    print("Risk parity weights:")
    for ticker, weight in weights.items():
        print(f"  {ticker}: {weight:.4f}")
