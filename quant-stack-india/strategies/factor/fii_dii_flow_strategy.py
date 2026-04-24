"""
FII/DII Flow Strategy

Follows Foreign Institutional Investor (FII) and Domestic Institutional Investor (DII) flows.

Strategy logic:
- Go long when FII_net > +₹1000Cr for 3 consecutive days
- Go to cash when FII_net < -₹1000Cr
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class FIIDIIFlowStrategy(BaseStrategy):
    """
    FII/DII flow following strategy.
    
    Uses institutional flow data as a market timing signal.
    """
    
    def __init__(
        self,
        fii_threshold: float = 1000,  # ₹1000 Cr
        consecutive_days: int = 3,
        lookback_days: int = 30,
        name: str = "FIIDIIFlowStrategy"
    ):
        super().__init__(name=name)
        self.fii_threshold = fii_threshold
        self.consecutive_days = consecutive_days
        self.lookback_days = lookback_days
        
        self.parameters = {
            "fii_threshold": fii_threshold,
            "consecutive_days": consecutive_days,
            "lookback_days": lookback_days,
        }
    
    def fetch_fii_dii_data(self) -> Optional[pd.DataFrame]:
        """
        Fetch FII/DII data from NSE.
        
        Returns:
            DataFrame with FII/DII flows or None on failure
        """
        try:
            from data.fetchers.india_nse_fetcher import get_fii_dii_data
            
            data = get_fii_dii_data(days=self.lookback_days)
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch FII/DII data: {e}")
            return None
    
    def generate_signal(self, fii_data: Optional[pd.DataFrame] = None) -> str:
        """
        Generate market timing signal based on FII flows.
        
        Args:
            fii_data: FII/DII DataFrame (fetched if None)
            
        Returns:
            Signal: "LONG", "CASH", or "NEUTRAL"
        """
        if fii_data is None:
            fii_data = self.fetch_fii_dii_data()
        
        if fii_data is None or fii_data.empty:
            logger.warning("No FII/DII data available")
            return "NEUTRAL"
        
        # Ensure fii_net column exists
        if 'fii_net' not in fii_data.columns:
            logger.warning("fii_net column not found in data")
            return "NEUTRAL"
        
        # Get recent FII flows
        recent_flows = fii_data['fii_net'].head(self.consecutive_days)
        
        # Check for consecutive positive flows
        positive_streak = all(flow > self.fii_threshold for flow in recent_flows)
        
        # Check for negative flow
        latest_flow = fii_data['fii_net'].iloc[0]
        negative_flow = latest_flow < -self.fii_threshold
        
        if positive_streak:
            logger.info(f"FII positive streak detected: {recent_flows.tolist()}")
            return "LONG"
        elif negative_flow:
            logger.info(f"FII negative flow detected: {latest_flow}")
            return "CASH"
        
        return "NEUTRAL"
    
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
        signal = self.generate_signal()
        
        tickers = prices.columns.tolist()
        
        if signal == "LONG":
            # Equal weight all stocks
            weight = 1.0 / len(tickers) if tickers else 0
            return {ticker: weight for ticker in tickers}
        
        elif signal == "CASH":
            # No positions
            return {}
        
        else:  # NEUTRAL
            # Maintain current positions (equal weight)
            weight = 1.0 / len(tickers) if tickers else 0
            return {ticker: weight for ticker in tickers}
    
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
