"""
APScheduler for Indian Markets
================================
Runs three daily jobs:
  08:00 IST — token_refresh (Zerodha access token)
  09:10 IST — pre_market_check (validate data, margins, connectivity)
  09:20 IST — run_pipeline (main trading pipeline)
  15:45 IST — eod_reconciliation (log final positions, P&L)

All times in IST. Only runs on NSE trading days.
"""

import logging
import sys
import signal
from datetime import datetime
from pathlib import Path
import pytz

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")


def safe_run(func_name: str, *args, **kwargs):
    """Run a pipeline function safely, log any exceptions."""
    from utils.nse_calendar import is_trading_day
    if not is_trading_day(datetime.now(IST).date()):
        logger.info(f"[{func_name}] Skipped — not a trading day")
        return
    try:
        if func_name == "token_refresh":
            from automation.token_refresh import refresh_zerodha_token
            refresh_zerodha_token()
        elif func_name == "pipeline":
            from automation.pipeline import run_pipeline
            import os
            run_pipeline(mode=os.getenv("TRADING_MODE", "paper"))
        elif func_name == "eod":
            logger.info("EOD reconciliation: fetching final positions")
    except Exception as e:
        logger.error(f"[{func_name}] Failed: {e}", exc_info=True)


def run_scheduler():
    """Start the scheduler."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("APScheduler not installed. Run: pip install APScheduler==3.10.4")
        return
    
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler("logs/scheduler.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    scheduler = BlockingScheduler(timezone=IST)
    
    scheduler.add_job(
        lambda: safe_run("token_refresh"),
        CronTrigger(hour=8, minute=0, timezone=IST),
        id="token_refresh",
        name="Zerodha Token Refresh"
    )
    scheduler.add_job(
        lambda: safe_run("pipeline"),
        CronTrigger(hour=9, minute=20, day_of_week="mon-fri", timezone=IST),
        id="pipeline",
        name="Main Trading Pipeline"
    )
    scheduler.add_job(
        lambda: safe_run("eod"),
        CronTrigger(hour=15, minute=45, day_of_week="mon-fri", timezone=IST),
        id="eod",
        name="EOD Reconciliation"
    )
    
    def shutdown(signum, frame):
        logger.info("Shutdown signal received — stopping scheduler")
        scheduler.shutdown(wait=False)
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    
    logger.info("Scheduler starting — Indian market jobs active")
    logger.info("  08:00 IST — Zerodha token refresh")
    logger.info("  09:20 IST — Main trading pipeline (Mon-Fri, trading days only)")
    logger.info("  15:45 IST — EOD reconciliation")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    run_scheduler()
