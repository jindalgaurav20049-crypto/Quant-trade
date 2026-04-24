"""
Quality-Value Factor Strategy

Combines quality metrics (ROE) with value metrics (P/E, P/B)
to select stocks with strong fundamentals at reasonable prices.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class QualityValueStrategy(BaseStrategy):
    """
    Quality-Value factor strategy.
    
    Scores stocks based on:
    - Low P/E (value)
    - Low P/B (value)
    - High ROE (quality)
    """
    
    def __init__(
        self,
        pe_weight: float = 0.3,
        pb_weight: float = 0.3,
        roe_weight: float = 0.4,
        top_n: int = 10,
        name: str = "QualityValueStrategy"
    ):
        super().__init__(name=name)
        self.pe_weight = pe_weight
        self.pb_weight = pb_weight
        self.roe_weight = roe_weight
        self.top_n = top_n
        
        self.parameters = {
            "pe_weight": pe_weight,
            "pb_weight": pb_weight,
            "roe_weight": roe_weight,
            "top_n": top_n,
        }
    
    def fetch_fundamentals(self, tickers: List[str]) -> pd.DataFrame:
        """
        Fetch fundamental data for tickers.
        
        Args:
            tickers: List of stock symbols
            
        Returns:
            DataFrame with fundamentals
        """
        fundamentals = []
        
        for ticker in tickers:
            try:
                from data.fetchers.yfinance_fetcher import fetch_fundamentals
                
                data = fetch_fundamentals(ticker)
                
                fundamentals.append({
                    'ticker': ticker,
                    'pe': data.get('pe_ratio'),
                    'pb': data.get('pb_ratio'),
                    'roe': data.get('roe'),
                })
                
            except Exception as e:
                logger.warning(f"Failed to fetch fundamentals for {ticker}: {e}")
        
        return pd.DataFrame(fundamentals)
    
    def compute_zscore(self, series: pd.Series) -> pd.Series:
        """
        Compute z-score for a series.
        
        Args:
            series: Input series
            
        Returns:
            Z-score series
        """
        mean = series.mean()
        std = series.std()
        
        if std == 0:
            return pd.Series(0, index=series.index)
        
        return (series - mean) / std
    
    def compute_scores(self, fundamentals: pd.DataFrame) -> pd.Series:
        """
        Compute composite quality-value scores.
        
        Args:
            fundamentals: DataFrame with PE, PB, ROE
            
        Returns:
            Series of composite scores
        """
        df = fundamentals.copy()
        
        # Remove rows with missing data
        df = df.dropna(subset=['pe', 'pb', 'roe'])
        
        if df.empty:
            return pd.Series(dtype=float)
        
        # Compute z-scores
        df['pe_zscore'] = self.compute_zscore(df['pe'])
        df['pb_zscore'] = self.compute_zscore(df['pb'])
        df['roe_zscore'] = self.compute_zscore(df['roe'])
        
        # For PE and PB, lower is better (multiply by -1)
        # For ROE, higher is better
        df['composite_score'] = (
            -self.pe_weight * df['pe_zscore'] +
            -self.pb_weight * df['pb_zscore'] +
            self.roe_weight * df['roe_zscore']
        )
        
        return df.set_index('ticker')['composite_score']
    
    def select_stocks(self, scores: pd.Series) -> List[str]:
        """
        Select top N stocks by score.
        
        Args:
            scores: Series of composite scores
            
        Returns:
            List of selected tickers
        """
        if scores.empty:
            return []
        
        sorted_scores = scores.sort_values(ascending=False)
        selected = sorted_scores.head(self.top_n).index.tolist()
        
        logger.info(f"Selected {len(selected)} quality-value stocks")
        return selected
    
    def generate_signals(
        self,
        prices: pd.DataFrame,
        **kwargs
    ) -> Dict[str, float]:
        """
        Generate trading signals.
        
        Args:
            prices: DataFrame with price data
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of ticker to target weight
        """
        tickers = prices.columns.tolist()
        
        # Fetch fundamentals
        fundamentals = self.fetch_fundamentals(tickers)
        
        if fundamentals.empty:
            logger.warning("No fundamental data available")
            return {}
        
        # Compute scores
        scores = self.compute_scores(fundamentals)
        
        # Select stocks
        selected = self.select_stocks(scores)
        
        # Equal weight
        if selected:
            weight = 1.0 / len(selected)
            return {ticker: weight for ticker in selected}
        
        return {}
    
    def compute_weights(
        self,
        signals: Dict[str, float],
        **kwargs
    ) -> Dict[str, float]:
        """
        Convert signals to portfolio weights.
        
        Args:
            signals: Dictionary of signals
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of ticker to weight
        """
        return signals
