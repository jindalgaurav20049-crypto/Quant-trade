"""
Performance Report Generator

Generates comprehensive performance reports with metrics and visualizations.
"""

import logging
from typing import Dict, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class PerformanceReport:
    """
    Generate performance reports for backtests.
    """
    
    def __init__(self, returns: pd.Series, benchmark: Optional[pd.Series] = None):
        """
        Initialize report.
        
        Args:
            returns: Strategy returns series
            benchmark: Optional benchmark returns
        """
        self.returns = returns.dropna()
        self.benchmark = benchmark.dropna() if benchmark is not None else None
    
    def calculate_metrics(self) -> Dict:
        """
        Calculate performance metrics.
        
        Returns:
            Dictionary of metrics
        """
        if self.returns.empty:
            return {}
        
        # Total return
        total_return = (1 + self.returns).prod() - 1
        
        # Annualized return
        n_years = len(self.returns) / 252
        cagr = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0
        
        # Volatility
        volatility = self.returns.std() * np.sqrt(252)
        
        # Sharpe ratio
        sharpe = cagr / volatility if volatility > 0 else 0
        
        # Max drawdown
        cumulative = (1 + self.returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Calmar ratio
        calmar = cagr / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Win rate
        win_rate = (self.returns > 0).mean()
        
        # Profit factor
        gains = self.returns[self.returns > 0].sum()
        losses = abs(self.returns[self.returns < 0].sum())
        profit_factor = gains / losses if losses > 0 else 0
        
        metrics = {
            'total_return': total_return,
            'cagr': cagr,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
        }
        
        # Benchmark metrics
        if self.benchmark is not None:
            benchmark_return = (1 + self.benchmark).prod() - 1
            benchmark_cagr = (1 + benchmark_return) ** (1 / n_years) - 1 if n_years > 0 else 0
            
            metrics['benchmark_cagr'] = benchmark_cagr
            metrics['alpha'] = cagr - benchmark_cagr
            
            # Beta
            covariance = self.returns.cov(self.benchmark)
            benchmark_variance = self.benchmark.var()
            beta = covariance / benchmark_variance if benchmark_variance > 0 else 1
            metrics['beta'] = beta
        
        return metrics
    
    def generate_report(self) -> str:
        """
        Generate text report.
        
        Returns:
            Report string
        """
        metrics = self.calculate_metrics()
        
        if not metrics:
            return "No data available for report."
        
        report = f"""
{'='*50}
PERFORMANCE REPORT
{'='*50}

Returns:
  Total Return:     {metrics['total_return']*100:>8.2f}%
  CAGR:             {metrics['cagr']*100:>8.2f}%

Risk Metrics:
  Volatility:       {metrics['volatility']*100:>8.2f}%
  Max Drawdown:     {metrics['max_drawdown']*100:>8.2f}%

Risk-Adjusted:
  Sharpe Ratio:     {metrics['sharpe_ratio']:>8.2f}
  Calmar Ratio:     {metrics['calmar_ratio']:>8.2f}

Trade Statistics:
  Win Rate:         {metrics['win_rate']*100:>8.2f}%
  Profit Factor:    {metrics['profit_factor']:>8.2f}
"""
        
        if 'benchmark_cagr' in metrics:
            report += f"""
Benchmark Comparison:
  Benchmark CAGR:   {metrics['benchmark_cagr']*100:>8.2f}%
  Alpha:            {metrics['alpha']*100:>8.2f}%
  Beta:             {metrics['beta']:>8.2f}
"""
        
        report += f"\n{'='*50}\n"
        
        return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test PerformanceReport ===")
    
    # Create sample returns
    dates = pd.date_range("2023-01-01", periods=252, freq='D')
    returns = pd.Series(np.random.randn(252) * 0.02, index=dates)
    benchmark = pd.Series(np.random.randn(252) * 0.015, index=dates)
    
    report = PerformanceReport(returns, benchmark)
    
    print(report.generate_report())
