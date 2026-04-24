"""
Tests for trading strategies.
"""

import unittest
import pandas as pd
import numpy as np


class TestMomentumFactorPortfolio(unittest.TestCase):
    """Test momentum factor portfolio strategy."""
    
    def setUp(self):
        """Set up test data."""
        dates = pd.date_range("2023-01-01", periods=300, freq='D')
        self.prices = pd.DataFrame({
            'RELIANCE.NS': 100 * (1 + np.random.randn(300).cumsum() * 0.01),
            'TCS.NS': 100 * (1 + np.random.randn(300).cumsum() * 0.01),
            'HDFCBANK.NS': 100 * (1 + np.random.randn(300).cumsum() * 0.01),
        }, index=dates)
    
    def test_compute_momentum_signal(self):
        """Test momentum signal computation."""
        from strategies.momentum.momentum_factor_portfolio import MomentumFactorPortfolio
        
        strategy = MomentumFactorPortfolio(universe_tickers=list(self.prices.columns))
        signals = strategy.compute_momentum_signal(self.prices)
        
        self.assertIsInstance(signals, pd.Series)
        self.assertEqual(len(signals), len(self.prices.columns))
    
    def test_select_portfolio(self):
        """Test portfolio selection."""
        from strategies.momentum.momentum_factor_portfolio import MomentumFactorPortfolio
        
        strategy = MomentumFactorPortfolio(
            universe_tickers=list(self.prices.columns),
            top_n=2
        )
        
        momentum = pd.Series({
            'RELIANCE.NS': 0.15,
            'TCS.NS': 0.10,
            'HDFCBANK.NS': 0.05,
        })
        
        long, short = strategy.select_portfolio(momentum)
        
        self.assertEqual(len(long), 2)
        self.assertIn('RELIANCE.NS', long)


class TestVolatilityTargeting(unittest.TestCase):
    """Test volatility targeting."""
    
    def test_compute_realised_vol(self):
        """Test realized volatility computation."""
        from strategies.volatility.volatility_targeting import VolatilityTargeting
        
        vt = VolatilityTargeting(vol_target=0.15)
        
        returns = pd.Series(np.random.randn(100) * 0.02)
        vol = vt.compute_realised_vol(returns)
        
        self.assertGreater(vol, 0)
        self.assertIsInstance(vol, float)
    
    def test_compute_vol_scalar(self):
        """Test volatility scalar computation."""
        from strategies.volatility.volatility_targeting import VolatilityTargeting
        
        vt = VolatilityTargeting(vol_target=0.15)
        
        returns = pd.Series(np.random.randn(100) * 0.02)
        scalar = vt.compute_vol_scalar(returns)
        
        self.assertGreaterEqual(scalar, vt.min_scalar)
        self.assertLessEqual(scalar, vt.max_scalar)


if __name__ == "__main__":
    unittest.main()
