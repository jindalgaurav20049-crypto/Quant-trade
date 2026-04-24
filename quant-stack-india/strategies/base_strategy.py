"""
Abstract base class for all trading strategies.

Defines the interface that all strategies must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies.
    
    All strategies must inherit from this class and implement
    the required methods.
    """
    
    def __init__(self, name: Optional[str] = None):
        """
        Initialize the strategy.
        
        Args:
            name: Strategy name (defaults to class name)
        """
        self._name = name or self.__class__.__name__
        self.parameters = {}
        logger.info(f"Initialized strategy: {self._name}")
    
    @property
    def name(self) -> str:
        """Get strategy name."""
        return self._name
    
    @abstractmethod
    def generate_signals(
        self,
        prices: pd.DataFrame,
        **kwargs
    ) -> Dict[str, float]:
        """
        Generate trading signals.
        
        Args:
            prices: DataFrame with price data (dates x tickers)
            **kwargs: Additional strategy-specific parameters
            
        Returns:
            Dictionary mapping ticker to target weight
        """
        pass
    
    @abstractmethod
    def compute_weights(
        self,
        signals: Dict[str, float],
        **kwargs
    ) -> Dict[str, float]:
        """
        Compute portfolio weights from signals.
        
        Args:
            signals: Dictionary of raw signals
            **kwargs: Additional parameters
            
        Returns:
            Dictionary mapping ticker to portfolio weight
        """
        pass
    
    def weights_to_quantities(
        self,
        weights: Dict[str, float],
        portfolio_value: float,
        current_prices: Dict[str, float]
    ) -> Dict[str, int]:
        """
        Convert weights to integer share quantities.
        
        Args:
            weights: Dictionary of target weights
            portfolio_value: Total portfolio value
            current_prices: Dictionary of current prices per ticker
            
        Returns:
            Dictionary mapping ticker to share quantity
        """
        quantities = {}
        
        for ticker, weight in weights.items():
            if ticker not in current_prices or current_prices[ticker] <= 0:
                logger.warning(f"No valid price for {ticker}, skipping")
                continue
            
            target_value = portfolio_value * weight
            raw_qty = target_value / current_prices[ticker]
            quantities[ticker] = max(0, int(round(raw_qty)))
        
        return quantities
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get strategy parameters.
        
        Returns:
            Dictionary of parameter names and values
        """
        return self.parameters.copy()
    
    def set_parameters(self, **kwargs):
        """
        Set strategy parameters.
        
        Args:
            **kwargs: Parameters to set
        """
        self.parameters.update(kwargs)
        logger.info(f"Updated parameters for {self._name}: {kwargs}")
    
    def validate_data(self, prices: pd.DataFrame) -> bool:
        """
        Validate input data.
        
        Args:
            prices: Price DataFrame to validate
            
        Returns:
            True if data is valid
        """
        if prices.empty:
            logger.error("Empty price DataFrame")
            return False
        
        if len(prices) < 20:
            logger.warning(f"Limited price history: {len(prices)} rows")
        
        return True
    
    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(name='{self._name}')"
