"""
Volatility Targeting Strategy
==============================
Adjusts portfolio leverage daily so that the realised portfolio volatility
equals a target level (default 15% annualised). When markets are calm,
scale up exposure. When markets spike, scale down. This is the core
risk-management overlay used by most systematic funds.

Method:
  1. Compute EWMA (exponentially weighted) realised vol of portfolio returns
  2. vol_scalar = vol_target / realised_vol
  3. Clip scalar to [0.25, 2.0] to prevent extreme leverage
  4. Adjust position sizes by vol_scalar
  5. Apply India VIX override: if VIX > 20, cap scalar at 0.75; if VIX > 30, force scalar to 0
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class VolatilityTargeting:
    def __init__(
        self,
        vol_target: float = 0.15,
        ewma_span: int = 20,
        min_scalar: float = 0.25,
        max_scalar: float = 2.0,
        vix_reduce_threshold: float = 20.0,
        vix_halt_threshold: float = 30.0
    ):
        self.vol_target = vol_target
        self.ewma_span = ewma_span
        self.min_scalar = min_scalar
        self.max_scalar = max_scalar
        self.vix_reduce_threshold = vix_reduce_threshold
        self.vix_halt_threshold = vix_halt_threshold

    def compute_realised_vol(self, returns: pd.Series) -> float:
        """EWMA realised volatility, annualised (252 trading days)."""
        if len(returns) < 5:
            return self.vol_target  # not enough data, return target (scalar=1)
        ewma_var = returns.ewm(span=self.ewma_span, min_periods=5).var().iloc[-1]
        if np.isnan(ewma_var) or ewma_var <= 0:
            return self.vol_target
        return float(np.sqrt(ewma_var * 252))

    def compute_vol_scalar(
        self,
        portfolio_returns: pd.Series,
        india_vix: Optional[float] = None
    ) -> float:
        """
        Compute position scalar to hit vol target.
        Returns float in [min_scalar, max_scalar].
        """
        realised_vol = self.compute_realised_vol(portfolio_returns)
        if realised_vol < 1e-6:
            scalar = 1.0
        else:
            scalar = self.vol_target / realised_vol

        # India VIX override
        if india_vix is not None:
            if india_vix >= self.vix_halt_threshold:
                logger.warning(f"India VIX={india_vix:.1f} >= {self.vix_halt_threshold} — forcing scalar=0")
                return 0.0
            elif india_vix >= self.vix_reduce_threshold:
                vix_cap = 0.75
                scalar = min(scalar, vix_cap)
                logger.info(f"India VIX={india_vix:.1f} — capping scalar at {vix_cap}")

        scalar = float(np.clip(scalar, self.min_scalar, self.max_scalar))
        logger.info(f"Vol target: realised={realised_vol:.3f}, target={self.vol_target}, scalar={scalar:.3f}")
        return scalar

    def scale_positions(
        self,
        target_weights: Dict[str, float],
        portfolio_returns: pd.Series,
        india_vix: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Scale target weights by vol scalar.
        Input/output: dict of {ticker: weight}
        """
        scalar = self.compute_vol_scalar(portfolio_returns, india_vix)
        return {ticker: weight * scalar for ticker, weight in target_weights.items()}

    def scale_quantities(
        self,
        target_quantities: Dict[str, int],
        portfolio_returns: pd.Series,
        india_vix: Optional[float] = None
    ) -> Dict[str, int]:
        """
        Scale integer share quantities by vol scalar.
        Always rounds to nearest integer. NSE does not allow fractional shares.
        """
        scalar = self.compute_vol_scalar(portfolio_returns, india_vix)
        return {
            ticker: max(0, round(qty * scalar))
            for ticker, qty in target_quantities.items()
        }

    def run_backtest_overlay(
        self,
        raw_returns: pd.Series,
        look_back: int = 252
    ) -> pd.Series:
        """
        Apply vol targeting as an overlay to a return series.
        For each day, compute scalar using preceding look_back days, apply to next day return.
        Used to compare vol-targeted vs raw strategy performance in backtests.
        """
        scaled_returns = pd.Series(index=raw_returns.index, dtype=float)
        for i in range(look_back, len(raw_returns)):
            window = raw_returns.iloc[i - look_back:i]
            scalar = self.compute_vol_scalar(window)
            scaled_returns.iloc[i] = raw_returns.iloc[i] * scalar
        return scaled_returns.dropna()
