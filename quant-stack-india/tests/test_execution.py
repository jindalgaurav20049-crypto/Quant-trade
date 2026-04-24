"""
Tests for execution modules.
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd


class TestZerodhaBroker(unittest.TestCase):
    """Test Zerodha broker."""
    
    @patch.dict('os.environ', {'TRADING_MODE': 'paper', 'ZERODHA_API_KEY': ''})
    def test_paper_mode(self):
        """Test paper trading mode."""
        from execution.brokers.zerodha_broker import ZerodhaBroker
        
        broker = ZerodhaBroker()
        
        self.assertEqual(broker.trading_mode, 'paper')
    
    @patch.dict('os.environ', {'TRADING_MODE': 'paper'})
    def test_place_order_paper(self):
        """Test placing order in paper mode."""
        from execution.brokers.zerodha_broker import ZerodhaBroker
        
        broker = ZerodhaBroker()
        order_id = broker.place_order("RELIANCE.NS", 10, "BUY")
        
        self.assertIsNotNone(order_id)
        self.assertTrue(order_id.startswith("PAPER"))
    
    @patch.dict('os.environ', {'TRADING_MODE': 'paper'})
    def test_get_margins_paper(self):
        """Test getting margins in paper mode."""
        from execution.brokers.zerodha_broker import ZerodhaBroker
        
        broker = ZerodhaBroker()
        margins = broker.get_margins()
        
        self.assertIn('available', margins)
        self.assertEqual(margins['mode'], 'paper')


class TestOrderManager(unittest.TestCase):
    """Test order manager."""
    
    @patch.dict('os.environ', {'TRADING_MODE': 'paper', 'ACTIVE_BROKER': 'zerodha'})
    def test_order_manager(self):
        """Test order manager initialization."""
        from execution.order_manager import OrderManager
        
        manager = OrderManager()
        
        self.assertIsNotNone(manager.broker)


if __name__ == "__main__":
    unittest.main()
