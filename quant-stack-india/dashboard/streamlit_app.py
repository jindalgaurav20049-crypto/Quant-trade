"""
Streamlit Dashboard for quant-stack-india

Features:
- INR formatting
- IST timestamps
- India VIX gauge
- FII/DII flow charts
- Portfolio performance tracking
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

# Page config
st.set_page_config(
    page_title="quant-stack India",
    page_icon="☸",
    layout="wide"
)

IST = pytz.timezone("Asia/Kolkata")


def format_inr(value: float) -> str:
    """Format value in Indian numbering system."""
    if value >= 1e7:
        return f"₹{value/1e7:.2f}Cr"
    elif value >= 1e5:
        return f"₹{value/1e5:.2f}L"
    else:
        return f"₹{value:,.2f}"


def get_market_status():
    """Get current market status."""
    from utils.nse_calendar import is_market_open, get_market_status_message
    return get_market_status_message()


def main():
    """Main dashboard function."""
    
    st.title("☸ quant-stack India")
    st.markdown("*Algorithmic Trading for NSE/BSE*")
    
    # Sidebar
    st.sidebar.header("Settings")
    
    # Market status
    market_status = get_market_status()
    if "OPEN" in market_status:
        st.sidebar.success(market_status)
    else:
        st.sidebar.info(market_status)
    
    # Current time in IST
    now_ist = datetime.now(IST)
    st.sidebar.text(f"IST: {now_ist.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Main content
    tab1, tab2, tab3 = st.tabs(["Portfolio", "Market Data", "Strategy Performance"])
    
    with tab1:
        st.header("Portfolio Overview")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Portfolio Value", format_inr(1000000), "+₹50,000")
        with col2:
            st.metric("Day P&L", format_inr(50000), "+5.0%")
        with col3:
            st.metric("Total Return", "+15.2%", "+2.1%")
        with col4:
            st.metric("Sharpe Ratio", "1.25", "+0.05")
        
        # Placeholder for equity curve
        st.subheader("Equity Curve")
        chart_data = pd.DataFrame(
            np.random.randn(100, 2).cumsum(axis=0) + 100,
            columns=['Portfolio', 'Nifty 50'],
            index=pd.date_range("2023-01-01", periods=100)
        )
        st.line_chart(chart_data)
    
    with tab2:
        st.header("Market Data")
        
        # India VIX
        st.subheader("India VIX")
        vix_col1, vix_col2 = st.columns(2)
        
        with vix_col1:
            try:
                from data.fetchers.india_nse_fetcher import get_india_vix
                vix = get_india_vix()
                if vix:
                    if vix < 15:
                        st.success(f"VIX: {vix:.2f} (Low)")
                    elif vix < 20:
                        st.info(f"VIX: {vix:.2f} (Normal)")
                    elif vix < 25:
                        st.warning(f"VIX: {vix:.2f} (Elevated)")
                    else:
                        st.error(f"VIX: {vix:.2f} (High)")
                else:
                    st.warning("VIX data unavailable")
            except Exception as e:
                st.error(f"Failed to fetch VIX: {e}")
        
        # FII/DII flows
        st.subheader("FII/DII Flows")
        try:
            from data.fetchers.india_nse_fetcher import get_fii_dii_data
            fii_dii = get_fii_dii_data(days=30)
            if not fii_dii.empty:
                st.bar_chart(fii_dii[['fii_net', 'dii_net']].head(10))
            else:
                st.warning("FII/DII data unavailable")
        except Exception as e:
            st.error(f"Failed to fetch FII/DII: {e}")
    
    with tab3:
        st.header("Strategy Performance")
        
        # Strategy metrics
        strategies = pd.DataFrame({
            'Strategy': ['Momentum Factor', 'Volatility Targeting', 'Pairs Trading', 'Bollinger Reversion'],
            'CAGR': ['18.5%', '12.3%', '14.2%', '16.1%'],
            'Sharpe': [1.15, 1.05, 1.25, 1.08],
            'Max DD': ['-15.2%', '-10.5%', '-8.3%', '-12.1%'],
        })
        
        st.dataframe(strategies, use_container_width=True)
        
        # Current positions
        st.subheader("Current Positions")
        positions = pd.DataFrame({
            'Ticker': ['RELIANCE', 'TCS', 'HDFCBANK'],
            'Qty': [10, 5, 15],
            'Avg Price': [2500, 3500, 1500],
            'Current': [2600, 3600, 1550],
            'P&L': [1000, 500, 750],
        })
        st.dataframe(positions, use_container_width=True)


if __name__ == "__main__":
    main()
