"""
Tests for risk management modules.
"""

import unittest
import pandas as pd
import numpy as np


class TestPositionSizer(unittest.TestCase):
    """Test position sizer."""
    
    def test_round_to_lot_size(self):
        """Test lot size rounding."""
        from risk.position_sizer import round_to_lot_size
        
        # CNC should not round
        self.assertEqual(round_to_lot_size(105, "RELIANCE.NS", "CNC"), 105)
        
        # NRML should round to lot size
        result = round_to_lot_size(80, "NIFTY", "NRML")
        self.assertEqual(result % 75, 0)  # Should be multiple of 75
    
    def test_kelly_size(self):
        """Test Kelly criterion sizing."""
        from risk.position_sizer import kelly_size
        
        size = kelly_size(win_rate=0.55, avg_win=0.05, avg_loss=0.03)
        
        self.assertGreater(size, 0)
        self.assertLessEqual(size, 0.25)
    
    def test_fixed_fractional_qty(self):
        """Test fixed fractional sizing."""
        from risk.position_sizer import fixed_fractional_qty
        
        qty = fixed_fractional_qty(
            portfolio_value=1000000,
            ticker_price=2500,
            fraction=0.05
        )
        
        self.assertGreater(qty, 0)


class TestCircuitBreakers(unittest.TestCase):
    """Test circuit breakers."""
    
    def test_get_circuit_band(self):
        """Test circuit band retrieval."""
        from risk.circuit_breakers import get_circuit_band
        
        # Nifty 50 stocks should be A-group (20%)
        self.assertEqual(get_circuit_band("RELIANCE.NS"), 0.20)
        
        # Unknown stocks should use default
        self.assertEqual(get_circuit_band("UNKNOWN.NS"), 0.10)
    
    def test_check_order_within_band(self):
        """Test order validation."""
        from risk.circuit_breakers import check_order_within_band
        
        # Valid order
        valid, reason = check_order_within_band("RELIANCE.NS", 2600, 2500)
        self.assertTrue(valid)
        
        # Invalid order (above upper band)
        valid, reason = check_order_within_band("RELIANCE.NS", 3200, 2500)
        self.assertFalse(valid)


if __name__ == "__main__":
    unittest.main()
