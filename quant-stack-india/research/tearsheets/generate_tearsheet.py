"""
Generate Tearsheets

Creates PDF/HTML tearsheets for strategy performance reports.
"""

import logging
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)


def generate_tearsheet(
    returns: pd.Series,
    benchmark: Optional[pd.Series] = None,
    output_path: str = "tearsheet.html"
) -> bool:
    """
    Generate performance tearsheet.
    
    Args:
        returns: Strategy returns series
        benchmark: Optional benchmark returns
        output_path: Output file path
        
    Returns:
        True if successful
    """
    try:
        import pyfolio as pf
        
        # Generate tearsheet
        pf.create_full_tear_sheet(
            returns,
            benchmark_rets=benchmark,
            return_fig=False
        )
        
        logger.info(f"Tearsheet generated: {output_path}")
        return True
        
    except ImportError:
        logger.warning("pyfolio not installed, using basic report")
        
        # Fallback to basic report
        from backtesting.results.performance_report import PerformanceReport
        
        report = PerformanceReport(returns, benchmark)
        
        with open(output_path, 'w') as f:
            f.write("<html><body><pre>")
            f.write(report.generate_report())
            f.write("</pre></body></html>")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate tearsheet: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create sample data
    import numpy as np
    dates = pd.date_range("2023-01-01", periods=252, freq='D')
    returns = pd.Series(np.random.randn(252) * 0.02, index=dates)
    
    generate_tearsheet(returns, output_path="/tmp/test_tearsheet.html")
