"""Dashboard modules."""

from .plotly_charts import (
    equity_curve_chart,
    drawdown_chart,
    factor_exposure_chart,
    fii_dii_flow_chart,
)

__all__ = [
    "equity_curve_chart",
    "drawdown_chart",
    "factor_exposure_chart",
    "fii_dii_flow_chart",
]
