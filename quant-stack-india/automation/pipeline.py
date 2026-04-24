"""
Indian Market Trading Pipeline
================================
Full pipeline: token refresh → data → signals → risk → execute → log → alert

Runs at 09:20 IST on NSE trading days (5 min after market open).
Pre-market validation at 09:10 IST.
EOD reconciliation at 15:45 IST.
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path
import pytz

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")


def run_pipeline(mode: str = "paper", force: bool = False) -> bool:
    """
    Execute full trading pipeline.
    Returns True on success, False on any critical failure.
    """
    now_ist = datetime.now(IST)
    logger.info(f"=== Pipeline starting at {now_ist.strftime('%Y-%m-%d %H:%M:%S IST')} ===")
    logger.info(f"Mode: {mode.upper()}")

    # Step 0: Validate environment
    try:
        from utils.validate_setup import run_validation
        ok, errors = run_validation(silent=True)
        if not ok and not force:
            logger.error(f"Validation failed: {errors}")
            return False
    except Exception as e:
        logger.warning(f"Validation skipped: {e}")

    # Step 1: Check NSE calendar
    try:
        from utils.nse_calendar import is_trading_day, is_market_open
        if not is_trading_day(now_ist.date()) and not force:
            logger.info("Not a trading day — pipeline skipped")
            return True
    except Exception as e:
        logger.warning(f"Calendar check failed: {e}")

    # Step 2: Initialize broker
    try:
        broker_name = os.getenv("ACTIVE_BROKER", "zerodha")
        if broker_name == "zerodha":
            from execution.brokers.zerodha_broker import ZerodhaBroker
            broker = ZerodhaBroker()
        elif broker_name == "angel":
            from execution.brokers.angel_broker import AngelBroker
            broker = AngelBroker()
        else:
            from execution.brokers.fyers_broker import FyersBroker
            broker = FyersBroker()
        logger.info(f"Broker initialized: {broker_name} ({mode} mode)")
    except Exception as e:
        logger.error(f"Broker init failed: {e}")
        return False

    # Step 3: Fetch OHLCV data
    try:
        from data.fetchers.yfinance_fetcher import fetch_multiple
        import yaml
        with open("config/settings.yaml") as f:
            cfg = yaml.safe_load(f)
        universe = cfg["universe"]["nifty50"] + cfg["universe"].get("nifty_midcap", [])
        prices_dict = fetch_multiple(universe, period="1y")
        valid_tickers = [t for t, df in prices_dict.items() if not df.empty and len(df) > 50]
        logger.info(f"Fetched data for {len(valid_tickers)}/{len(universe)} tickers")
    except Exception as e:
        logger.error(f"Data fetch failed: {e}")
        return False

    # Step 4: Fetch India VIX
    india_vix = None
    try:
        from data.fetchers.india_nse_fetcher import get_india_vix
        india_vix = get_india_vix()
        logger.info(f"India VIX: {india_vix}")
    except Exception as e:
        logger.warning(f"India VIX fetch failed: {e} — proceeding without VIX filter")

    # Step 5: Build price matrix for strategies
    import pandas as pd
    try:
        close_prices = pd.DataFrame({
            t: df["Close"] for t, df in prices_dict.items() if not df.empty
        }).dropna(how="all")
        logger.info(f"Price matrix: {close_prices.shape[0]} days x {close_prices.shape[1]} tickers")
    except Exception as e:
        logger.error(f"Price matrix construction failed: {e}")
        return False

    # Step 6: Generate strategy signals
    signals = {}
    try:
        from strategies.momentum.momentum_factor_portfolio import MomentumFactorPortfolio
        momentum_strat = MomentumFactorPortfolio(
            universe_tickers=valid_tickers,
            vol_target=cfg["risk"]["volatility_target_annual"],
        )
        portfolio_returns = close_prices.mean(axis=1).pct_change().dropna()
        momentum_signals = momentum_strat.generate_signals(close_prices, portfolio_returns, india_vix)
        signals["momentum_factor"] = momentum_signals
        logger.info(f"Momentum signals: {len(momentum_signals)} positions")
    except Exception as e:
        logger.warning(f"Momentum strategy failed: {e}")

    # Step 7: Aggregate signals and get portfolio weights
    try:
        if not signals:
            logger.warning("No signals generated — pipeline complete with no trades")
            return True
        final_weights = signals.get("momentum_factor", {})
    except Exception as e:
        logger.error(f"Signal aggregation failed: {e}")
        return False

    # Step 8: Risk checks
    try:
        from risk.circuit_breakers import validate_order_batch
        from risk.position_sizer import fixed_fractional_qty
        margins = broker.get_margins()
        portfolio_value = margins.get("available", {}).get("live_balance", 1_000_000)
        logger.info(f"Available capital: ₹{portfolio_value:,.0f}")
    except Exception as e:
        logger.warning(f"Risk check error: {e} — using default portfolio value ₹10L")
        portfolio_value = 1_000_000

    # Step 9: Convert weights to orders
    orders = []
    try:
        for ticker, weight in final_weights.items():
            clean_ticker = ticker.replace(".NS", "").replace(".BO", "")
            if ticker not in close_prices.columns or close_prices[ticker].empty:
                continue
            price = float(close_prices[ticker].iloc[-1])
            qty = max(1, int(round((portfolio_value * abs(weight)) / price)))
            side = "BUY" if weight > 0 else "SELL"
            orders.append({"ticker": clean_ticker, "qty": qty, "side": side, "price": 0.0})
        logger.info(f"Orders to place: {len(orders)}")
    except Exception as e:
        logger.error(f"Order construction failed: {e}")
        return False

    # Step 10: Place orders
    placed_orders = []
    for order in orders:
        try:
            order_id = broker.place_order(
                ticker=order["ticker"],
                qty=order["qty"],
                side=order["side"],
                product=cfg["execution"]["product_type"],
            )
            if order_id:
                placed_orders.append({**order, "order_id": order_id})
        except Exception as e:
            logger.error(f"Order failed for {order['ticker']}: {e}")
            continue

    logger.info(f"Orders placed: {len(placed_orders)}/{len(orders)}")

    # Step 11: Send Telegram alert
    try:
        from automation.alerts.telegram_alerts import send_pipeline_summary
        send_pipeline_summary(placed_orders, portfolio_value, india_vix, mode)
    except Exception as e:
        logger.warning(f"Telegram alert failed (non-critical): {e}")

    logger.info(f"=== Pipeline complete: {len(placed_orders)} orders placed ===")
    return True


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler("logs/pipeline.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    Path("logs").mkdir(exist_ok=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default=os.getenv("TRADING_MODE", "paper"), choices=["paper", "live"])
    parser.add_argument("--force", action="store_true", help="Run even on non-trading days")
    args = parser.parse_args()
    success = run_pipeline(mode=args.mode, force=args.force)
    sys.exit(0 if success else 1)
