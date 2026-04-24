"""
Plotly Charts

Chart generation functions for the Streamlit dashboard.
All values formatted in INR.
"""

import logging
from typing import Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def format_inr(value: float) -> str:
    """Format value as Indian Rupees."""
    if value >= 1e7:
        return f"₹{value/1e7:.2f}Cr"
    elif value >= 1e5:
        return f"₹{value/1e5:.2f}L"
    else:
        return f"₹{value:,.2f}"


def equity_curve_chart(
    portfolio_values: pd.Series,
    benchmark: Optional[pd.Series] = None,
    title: str = "Portfolio Performance"
):
    """
    Create equity curve chart.
    
    Args:
        portfolio_values: Portfolio value series
        benchmark: Optional benchmark series
        title: Chart title
        
    Returns:
        Plotly figure
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        logger.error("plotly not installed")
        return None
    
    fig = go.Figure()
    
    # Portfolio
    fig.add_trace(go.Scatter(
        x=portfolio_values.index,
        y=portfolio_values.values,
        mode='lines',
        name='Portfolio',
        line=dict(color='#1f77b4', width=2)
    ))
    
    # Benchmark
    if benchmark is not None:
        fig.add_trace(go.Scatter(
            x=benchmark.index,
            y=benchmark.values,
            mode='lines',
            name='Nifty 50',
            line=dict(color='#ff7f0e', width=2, dash='dash')
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Value (₹)',
        hovermode='x unified',
        yaxis_tickprefix='₹',
        yaxis_tickformat=',.0f',
    )
    
    return fig


def drawdown_chart(drawdowns: pd.Series, title: str = "Drawdown"):
    """
    Create drawdown chart.
    
    Args:
        drawdowns: Drawdown series
        title: Chart title
        
    Returns:
        Plotly figure
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        logger.error("plotly not installed")
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=drawdowns.index,
        y=drawdowns.values * 100,
        mode='lines',
        fill='tozeroy',
        name='Drawdown',
        line=dict(color='red', width=1),
        fillcolor='rgba(255, 0, 0, 0.2)'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Drawdown (%)',
        hovermode='x unified',
        yaxis_tickformat='.1f',
    )
    
    return fig


def factor_exposure_chart(exposures: pd.Series):
    """
    Create factor exposure bar chart.
    
    Args:
        exposures: Factor exposure series
        
    Returns:
        Plotly figure
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        logger.error("plotly not installed")
        return None
    
    colors = ['green' if x > 0 else 'red' for x in exposures.values]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=exposures.index,
        y=exposures.values,
        marker_color=colors,
    ))
    
    fig.update_layout(
        title='Factor Exposure',
        xaxis_title='Factor',
        yaxis_title='Exposure',
        yaxis_tickformat='.2f',
    )
    
    return fig


def fii_dii_flow_chart(fii_dii_data: pd.DataFrame):
    """
    Create FII/DII flow chart.
    
    Args:
        fii_dii_data: DataFrame with FII/DII data
        
    Returns:
        Plotly figure
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        logger.error("plotly not installed")
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=fii_dii_data.index,
        y=fii_dii_data['fii_net'],
        name='FII Net',
        marker_color='blue'
    ))
    
    fig.add_trace(go.Bar(
        x=fii_dii_data.index,
        y=fii_dii_data['dii_net'],
        name='DII Net',
        marker_color='orange'
    ))
    
    fig.update_layout(
        title='FII/DII Net Flows',
        xaxis_title='Date',
        yaxis_title='Flow (₹ Cr)',
        barmode='group',
        hovermode='x unified',
    )
    
    return fig


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test Plotly Charts ===")
    
    # Create sample data
    dates = pd.date_range("2023-01-01", periods=100, freq='D')
    portfolio = pd.Series(1000000 * (1 + np.random.randn(100).cumsum() * 0.01), index=dates)
    
    print("Creating equity curve chart...")
    fig = equity_curve_chart(portfolio)
    print(f"Chart created: {fig is not None}")
