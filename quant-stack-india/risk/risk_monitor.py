"""
Risk Monitor

Monitors portfolio risk metrics in real-time.
"""

import logging
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class RiskMonitor:
    """
    Monitor portfolio risk metrics.
    """
    
    def __init__(
        self,
        max_position_size: float = 0.10,
        max_portfolio_drawdown: float = 0.15,
        volatility_target: float = 0.15
    ):
        self.max_position_size = max_position_size
        self.max_portfolio_drawdown = max_portfolio_drawdown
        self.volatility_target = volatility_target
        
        self.peak_value = 0
        self.current_drawdown = 0
    
    def calculate_portfolio_value(
        self,
        positions: Dict[str, int],
        current_prices: Dict[str, float]
    ) -> float:
        """
        Calculate current portfolio value.
        
        Args:
            positions: Dictionary of ticker to quantity
            current_prices: Dictionary of ticker to price
            
        Returns:
            Portfolio value
        """
        total = 0
        for ticker, qty in positions.items():
            price = current_prices.get(ticker, 0)
            total += qty * price
        return total
    
    def calculate_drawdown(
        self,
        portfolio_value: float
    ) -> float:
        """
        Calculate current drawdown from peak.
        
        Args:
            portfolio_value: Current portfolio value
            
        Returns:
            Drawdown as percentage
        """
        if portfolio_value > self.peak_value:
            self.peak_value = portfolio_value
            self.current_drawdown = 0
        else:
            self.current_drawdown = (self.peak_value - portfolio_value) / self.peak_value
        
        return self.current_drawdown
    
    def check_drawdown_limit(self) -> bool:
        """
        Check if drawdown exceeds limit.
        
        Returns:
            True if drawdown is within limit
        """
        return self.current_drawdown < self.max_portfolio_drawdown
    
    def calculate_position_concentration(
        self,
        positions: Dict[str, int],
        current_prices: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate position concentration.
        
        Args:
            positions: Dictionary of ticker to quantity
            current_prices: Dictionary of ticker to price
            
        Returns:
            Dictionary of ticker to position weight
        """
        portfolio_value = self.calculate_portfolio_value(positions, current_prices)
        
        if portfolio_value == 0:
            return {}
        
        concentrations = {}
        for ticker, qty in positions.items():
            position_value = qty * current_prices.get(ticker, 0)
            concentrations[ticker] = position_value / portfolio_value
        
        return concentrations
    
    def check_position_limits(
        self,
        positions: Dict[str, int],
        current_prices: Dict[str, float]
    ) -> List[str]:
        """
        Check if any positions exceed size limits.
        
        Args:
            positions: Dictionary of ticker to quantity
            current_prices: Dictionary of ticker to price
            
        Returns:
            List of tickers exceeding limit
        """
        concentrations = self.calculate_position_concentration(positions, current_prices)
        
        violations = [
            ticker for ticker, weight in concentrations.items()
            if weight > self.max_position_size
        ]
        
        return violations
    
    def calculate_portfolio_volatility(
        self,
        returns: pd.Series
    ) -> float:
        """
        Calculate portfolio volatility.
        
        Args:
            returns: Series of portfolio returns
            
        Returns:
            Annualized volatility
        """
        if len(returns) < 20:
            return 0
        
        return returns.std() * np.sqrt(252)
    
    def check_volatility_target(
        self,
        returns: pd.Series
    ) -> bool:
        """
        Check if portfolio volatility is within target.
        
        Args:
            returns: Series of portfolio returns
            
        Returns:
            True if within target
        """
        vol = self.calculate_portfolio_volatility(returns)
        return vol <= self.volatility_target * 1.2  # Allow 20% buffer
    
    def get_risk_report(
        self,
        positions: Dict[str, int],
        current_prices: Dict[str, float],
        returns: Optional[pd.Series] = None
    ) -> Dict:
        """
        Generate comprehensive risk report.
        
        Args:
            positions: Dictionary of ticker to quantity
            current_prices: Dictionary of ticker to price
            returns: Optional series of portfolio returns
            
        Returns:
            Risk report dictionary
        """
        portfolio_value = self.calculate_portfolio_value(positions, current_prices)
        drawdown = self.calculate_drawdown(portfolio_value)
        
        report = {
            'portfolio_value': portfolio_value,
            'peak_value': self.peak_value,
            'current_drawdown': drawdown,
            'drawdown_ok': self.check_drawdown_limit(),
            'position_violations': self.check_position_limits(positions, current_prices),
        }
        
        if returns is not None:
            report['portfolio_volatility'] = self.calculate_portfolio_volatility(returns)
            report['volatility_ok'] = self.check_volatility_target(returns)
        
        return report
    
    def should_halt_trading(self) -> bool:
        """
        Check if trading should be halted due to risk limits.
        
        Returns:
            True if trading should halt
        """
        return not self.check_drawdown_limit()


if __name__ == "__main__":
    # Test the module
    logging.basicConfig(level=logging.INFO)
    
    monitor = RiskMonitor()
    
    positions = {
        "RELIANCE.NS": 100,
        "TCS.NS": 50,
    }
    
    prices = {
        "RELIANCE.NS": 2500,
        "TCS.NS": 3500,
    }
    
    print("=== Test calculate_portfolio_value ===")
    value = monitor.calculate_portfolio_value(positions, prices)
    print(f"Portfolio value: ₹{value:,.2f}")
    
    print("\n=== Test calculate_position_concentration ===")
    concentrations = monitor.calculate_position_concentration(positions, prices)
    print(f"Concentrations: {concentrations}")
    
    print("\n=== Test check_position_limits ===")
    violations = monitor.check_position_limits(positions, prices)
    print(f"Violations: {violations}")
    
    print("\n=== Test get_risk_report ===")
    report = monitor.get_risk_report(positions, prices)
    for key, value in report.items():
        print(f"{key}: {value}")
