"""
India VIX Regime Filter
========================
Uses India VIX (NSE's volatility index) to classify market regimes
and adjust strategy aggressiveness accordingly.

Regime classification:
  LOW:    VIX < 15     → full exposure, momentum works best
  NORMAL: 15 <= VIX < 20 → normal exposure
  ELEVATED: 20 <= VIX < 25 → reduce to 75% exposure
  HIGH:   25 <= VIX < 30 → reduce to 50% exposure
  EXTREME: VIX >= 30   → cash only, no new positions
"""

import pandas as pd
import numpy as np
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class VIXRegime(Enum):
    LOW = "low"
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    EXTREME = "extreme"


REGIME_EXPOSURE = {
    VIXRegime.LOW: 1.00,
    VIXRegime.NORMAL: 1.00,
    VIXRegime.ELEVATED: 0.75,
    VIXRegime.HIGH: 0.50,
    VIXRegime.EXTREME: 0.00,
}


def classify_vix_regime(vix_level: Optional[float]) -> VIXRegime:
    if vix_level is None:
        logger.warning("VIX unavailable — defaulting to NORMAL regime")
        return VIXRegime.NORMAL
    if vix_level >= 30:
        return VIXRegime.EXTREME
    elif vix_level >= 25:
        return VIXRegime.HIGH
    elif vix_level >= 20:
        return VIXRegime.ELEVATED
    elif vix_level >= 15:
        return VIXRegime.NORMAL
    else:
        return VIXRegime.LOW


def get_exposure_scalar(vix_level: Optional[float]) -> float:
    regime = classify_vix_regime(vix_level)
    scalar = REGIME_EXPOSURE[regime]
    logger.info(f"India VIX={vix_level} → Regime={regime.value} → Exposure scalar={scalar}")
    return scalar


def add_vix_regime_column(df: pd.DataFrame, vix_col: str = "india_vix") -> pd.DataFrame:
    """Add regime and exposure columns to a DataFrame that has an india_vix column."""
    if vix_col not in df.columns:
        logger.warning(f"Column '{vix_col}' not found — defaulting all regimes to NORMAL")
        df["vix_regime"] = VIXRegime.NORMAL.value
        df["vix_exposure_scalar"] = 1.0
        return df
    df["vix_regime"] = df[vix_col].apply(lambda v: classify_vix_regime(v).value)
    df["vix_exposure_scalar"] = df[vix_col].apply(get_exposure_scalar)
    return df
