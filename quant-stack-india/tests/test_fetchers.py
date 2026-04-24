"""
Tests for data fetchers.

Uses mocking to avoid real network calls.
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np


class TestYFinanceFetcher(unittest.TestCase):
    """Test yfinance fetcher."""
    
    @patch('data.fetchers.yfinance_fetcher.yf.Ticker')
    def test_fetch_ohlcv(self, mock_ticker):
        """Test fetch_ohlcv function."""
        # Mock response
        mock_data = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [103, 104, 105],
            'Low': [99, 100, 101],
            'Close': [101, 102, 103],
            'Volume': [1000, 2000, 3000],
        }, index=pd.date_range("2024-01-01", periods=3))
        mock_data.index = mock_data.index.tz_localize('UTC')
        
        mock_instance = MagicMock()
        mock_instance.history.return_value = mock_data
        mock_ticker.return_value = mock_instance
        
        from data.fetchers.yfinance_fetcher import fetch_ohlcv
        result = fetch_ohlcv("RELIANCE")
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertIn('Close', result.columns)
    
    def test_add_suffix(self):
        """Test ticker suffix addition."""
        from data.fetchers.yfinance_fetcher import _add_suffix
        
        self.assertEqual(_add_suffix("RELIANCE"), "RELIANCE.NS")
        self.assertEqual(_add_suffix("RELIANCE.NS"), "RELIANCE.NS")
        self.assertEqual(_add_suffix("RELIANCE.BO"), "RELIANCE.BO")


class TestNSEFetcher(unittest.TestCase):
    """Test NSE fetcher."""
    
    def test_get_nifty500_constituents(self):
        """Test getting Nifty 500 constituents."""
        from data.fetchers.india_nse_fetcher import get_nifty500_constituents
        
        constituents = get_nifty500_constituents()
        
        self.assertIsInstance(constituents, list)
        self.assertGreater(len(constituents), 0)
        self.assertTrue(all('.NS' in t for t in constituents))


if __name__ == "__main__":
    unittest.main()
