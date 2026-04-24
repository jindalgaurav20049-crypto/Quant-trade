"""Volatility-based strategies."""

from .volatility_targeting import VolatilityTargeting
from .india_vix_regime import (
    VIXRegime,
    classify_vix_regime,
    get_exposure_scalar,
    add_vix_regime_column,
)

__all__ = [
    "VolatilityTargeting",
    "VIXRegime",
    "classify_vix_regime",
    "get_exposure_scalar",
    "add_vix_regime_column",
]
