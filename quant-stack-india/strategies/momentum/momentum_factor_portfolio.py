"""
Momentum Factor Portfolio — Indian Markets
==========================================
Cross-sectional momentum strategy on NSE universe (Nifty 500 subset).

Strategy logic:
  1. Universe: top 100 liquid NSE stocks by avg daily value traded
  2. Momentum signal: 12-month return excluding last 1 month (12-1 momentum)
     to avoid short-term reversal contamination
  3. Ranking: rank all stocks by momentum signal each month
  4. Portfolio: long top decile (10 stocks), optionally short bottom decile
  5. Rebalancing: monthly on last trading day of each month
  6. Position sizing: equal weight within long/short book, scaled by vol targeting
  7. Risk overlay: vol targeting (15% ann.) + India VIX filter

Historical evidence: 12-1 momentum on Indian large-caps has delivered
~18-22% annualised returns (gross) over 2010-2023 in academic studies.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from strategies.base_strategy import BaseStrategy
from strategies.volatility.volatility_targeting import VolatilityTargeting
from strategies.volatility.india_vix_regime import get_exposure_scalar

logger = logging.getLogger(__name__)


class MomentumFactorPortfolio(BaseStrategy):
    def __init__(
        self,
        universe_tickers: List[str],
        lookback_months: int = 12,
        skip_months: int = 1,
        long_decile: float = 0.10,
        short_decile: float = 0.10,
        long_short: bool = False,
        vol_target: float = 0.15,
        rebalance_freq: str = "monthly",
        top_n: int = 10,
    ):
        super().__init__(name="MomentumFactorPortfolio")
        self.universe_tickers = universe_tickers
        self.lookback_months = lookback_months
        self.skip_months = skip_months
        self.long_decile = long_decile
        self.short_decile = short_decile
        self.long_short = long_short
        self.vol_target = vol_target
        self.rebalance_freq = rebalance_freq
        self.top_n = top_n
        self.vol_targeter = VolatilityTargeting(vol_target=vol_target)
        
        self.parameters = {
            "lookback_months": lookback_months,
            "skip_months": skip_months,
            "long_decile": long_decile,
            "short_decile": short_decile,
            "long_short": long_short,
            "vol_target": vol_target,
            "rebalance_freq": rebalance_freq,
            "top_n": top_n,
        }

    def compute_momentum_signal(
        self, prices: pd.DataFrame, as_of_date: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        """
        12-1 momentum: total return from T-12months to T-1month.
        Prices: DataFrame with dates as index, tickers as columns.
        Returns pd.Series of momentum scores indexed by ticker.
        """
        if as_of_date is None:
            as_of_date = prices.index[-1]
        
        end_date = as_of_date - pd.DateOffset(months=self.skip_months)
        start_date = as_of_date - pd.DateOffset(months=self.lookback_months)
        
        prices_in_window = prices.loc[
            (prices.index >= start_date) & (prices.index <= end_date)
        ]
        
        if len(prices_in_window) < 20:
            logger.warning(f"Insufficient data for momentum calc on {as_of_date}. Need 20+ rows, got {len(prices_in_window)}")
            return pd.Series(dtype=float)
        
        momentum = (prices_in_window.iloc[-1] / prices_in_window.iloc[0]) - 1.0
        return momentum.dropna()

    def select_portfolio(
        self, momentum_scores: pd.Series
    ) -> Tuple[List[str], List[str]]:
        """
        Rank by momentum score, return (long_tickers, short_tickers).
        """
        if momentum_scores.empty:
            return [], []
        
        ranked = momentum_scores.rank(ascending=False)
        n = len(ranked)
        top_n = max(1, round(n * self.long_decile))
        bottom_n = max(1, round(n * self.short_decile))
        
        long_tickers = ranked[ranked <= top_n].index.tolist()
        short_tickers = ranked[ranked > n - bottom_n].index.tolist() if self.long_short else []
        
        logger.info(f"Momentum portfolio: {len(long_tickers)} long, {len(short_tickers)} short")
        return long_tickers, short_tickers

    def compute_weights(
        self,
        long_tickers: List[str],
        short_tickers: List[str],
        portfolio_returns: Optional[pd.Series] = None,
        india_vix: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Equal weight within long and short books.
        Applies vol targeting and VIX regime scaling.
        """
        weights = {}
        
        if not long_tickers:
            return weights
        
        long_weight = 1.0 / len(long_tickers)
        for t in long_tickers:
            weights[t] = long_weight
        
        if self.long_short and short_tickers:
            short_weight = -1.0 / len(short_tickers)
            for t in short_tickers:
                weights[t] = short_weight
        
        # VIX regime scaling
        if india_vix is not None:
            scalar = get_exposure_scalar(india_vix)
            weights = {t: w * scalar for t, w in weights.items()}
        
        # Vol targeting overlay
        if portfolio_returns is not None and len(portfolio_returns) >= 10:
            weights = self.vol_targeter.scale_positions(weights, portfolio_returns, india_vix)
        
        return weights

    def generate_signals(
        self,
        prices: pd.DataFrame,
        portfolio_returns: Optional[pd.Series] = None,
        india_vix: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Main entry point. Returns dict of {ticker: target_weight}.
        """
        if not self.validate_data(prices):
            return {}
            
        momentum_scores = self.compute_momentum_signal(prices)
        if momentum_scores.empty:
            logger.warning("No momentum scores computed — returning empty signal")
            return {}
        long_tickers, short_tickers = self.select_portfolio(momentum_scores)
        weights = self.compute_weights(long_tickers, short_tickers, portfolio_returns, india_vix)
        return weights

    def weights_to_quantities(
        self,
        weights: Dict[str, float],
        portfolio_value: float,
        current_prices: Dict[str, float],
    ) -> Dict[str, int]:
        """
        Convert target weights to integer share quantities.
        NSE does not allow fractional shares — always round to int.
        """
        quantities = {}
        for ticker, weight in weights.items():
            if ticker not in current_prices or current_prices[ticker] <= 0:
                logger.warning(f"No price for {ticker} — skipping")
                continue
            raw_qty = (portfolio_value * weight) / current_prices[ticker]
            quantities[ticker] = max(0, int(round(raw_qty)))
        return quantities
