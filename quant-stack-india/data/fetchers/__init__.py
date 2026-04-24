"""Data fetchers for various sources."""

from .yfinance_fetcher import fetch_ohlcv, fetch_multiple, fetch_index, fetch_india_vix
from .india_nse_fetcher import (
    get_live_quote,
    get_fii_dii_data,
    get_option_chain,
    get_india_vix,
    get_historical_data,
    get_nifty500_constituents,
)
from .fred_fetcher import fetch_fred_data, fetch_macro_indicators

__all__ = [
    "fetch_ohlcv",
    "fetch_multiple",
    "fetch_index",
    "fetch_india_vix",
    "get_live_quote",
    "get_fii_dii_data",
    "get_option_chain",
    "get_historical_data",
    "get_nifty500_constituents",
    "fetch_fred_data",
    "fetch_macro_indicators",
]
