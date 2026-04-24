"""
Portfolio Optimizer

Mean-variance optimization using PyPortfolioOpt.
Handles singular covariance matrix with Ledoit-Wolf shrinkage.
"""

import logging
from typing import Dict, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    """
    Mean-variance portfolio optimizer.
    """
    
    def __init__(self, risk_free_rate: float = 0.06):
        """
        Initialize optimizer.
        
        Args:
            risk_free_rate: Annual risk-free rate
        """
        self.risk_free_rate = risk_free_rate
    
    def optimize_max_sharpe(
        self,
        returns: pd.DataFrame,
        cov_matrix: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """
        Optimize for maximum Sharpe ratio.
        
        Args:
            returns: Returns DataFrame
            cov_matrix: Optional covariance matrix
            
        Returns:
            Dictionary of optimal weights
        """
        try:
            from pypfopt import EfficientFrontier, risk_models
            
            if cov_matrix is None:
                # Use Ledoit-Wolf shrinkage for stability
                cov_matrix = risk_models.CovarianceShrinkage(returns).ledoit_wolf()
            
            ef = EfficientFrontier(
                returns.mean() * 252,  # Annualized returns
                cov_matrix,
                weight_bounds=(0, 0.2)  # Max 20% in any stock
            )
            
            weights = ef.max_sharpe(risk_free_rate=self.risk_free_rate)
            
            return dict(weights)
            
        except Exception as e:
            logger.error(f"Max Sharpe optimization failed: {e}")
            # Fallback to equal weight
            n = len(returns.columns)
            return {col: 1.0 / n for col in returns.columns}
    
    def optimize_min_volatility(
        self,
        returns: pd.DataFrame,
        cov_matrix: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """
        Optimize for minimum volatility.
        
        Args:
            returns: Returns DataFrame
            cov_matrix: Optional covariance matrix
            
        Returns:
            Dictionary of optimal weights
        """
        try:
            from pypfopt import EfficientFrontier, risk_models
            
            if cov_matrix is None:
                cov_matrix = risk_models.CovarianceShrinkage(returns).ledoit_wolf()
            
            ef = EfficientFrontier(
                returns.mean() * 252,
                cov_matrix,
                weight_bounds=(0, 0.2)
            )
            
            weights = ef.min_volatility()
            
            return dict(weights)
            
        except Exception as e:
            logger.error(f"Min volatility optimization failed: {e}")
            n = len(returns.columns)
            return {col: 1.0 / n for col in returns.columns}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test PortfolioOptimizer ===")
    
    # Create sample returns
    dates = pd.date_range("2023-01-01", periods=252, freq='D')
    returns = pd.DataFrame({
        'RELIANCE.NS': np.random.randn(252) * 0.02,
        'TCS.NS': np.random.randn(252) * 0.018,
        'HDFCBANK.NS': np.random.randn(252) * 0.015,
    }, index=dates)
    
    optimizer = PortfolioOptimizer()
    
    print("\n=== Max Sharpe ===")
    weights = optimizer.optimize_max_sharpe(returns)
    print(weights)
    
    print("\n=== Min Volatility ===")
    weights = optimizer.optimize_min_volatility(returns)
    print(weights)
