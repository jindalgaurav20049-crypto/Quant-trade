"""
NSE Trading Calendar and Market Hours

Handles NSE holidays, trading days, and market open/close times in IST.
"""

import datetime
from typing import List, Optional
import pytz

# NSE Trading Holidays (YYYY-MM-DD format)
NSE_HOLIDAYS = {
    2024: [
        '2024-01-22', '2024-03-25', '2024-04-09', '2024-04-14', '2024-04-17',
        '2024-04-21', '2024-05-23', '2024-06-17', '2024-07-17', '2024-08-15',
        '2024-10-02', '2024-11-01', '2024-11-15', '2024-11-20', '2024-12-25'
    ],
    2025: [
        '2025-01-26', '2025-02-26', '2025-03-14', '2025-03-31', '2025-04-10',
        '2025-04-14', '2025-04-18', '2025-05-01', '2025-08-15', '2025-08-27',
        '2025-10-02', '2025-10-21', '2025-10-22', '2025-11-05', '2025-12-25'
    ],
    2026: [
        '2026-01-26', '2026-03-03', '2026-03-20', '2026-04-02', '2026-04-03',
        '2026-04-06', '2026-04-14', '2026-05-01', '2026-08-15', '2026-09-16',
        '2026-10-02', '2026-11-09', '2026-11-10', '2026-12-25'
    ],
}

# Market hours in IST
MARKET_OPEN_TIME = datetime.time(9, 15)  # 09:15 AM
MARKET_CLOSE_TIME = datetime.time(15, 30)  # 03:30 PM
MARKET_PRE_OPEN_END = datetime.time(9, 7)  # Pre-open ends at 09:07 AM

IST = pytz.timezone("Asia/Kolkata")


def _parse_holiday_dates(year: int) -> List[datetime.date]:
    """Parse holiday strings to date objects for a given year."""
    if year not in NSE_HOLIDAYS:
        return []
    return [datetime.datetime.strptime(d, '%Y-%m-%d').date() for d in NSE_HOLIDAYS[year]]


def is_trading_day(date: datetime.date) -> bool:
    """
    Check if a given date is an NSE trading day.
    
    Returns False for weekends and NSE holidays.
    
    Args:
        date: Date to check
        
    Returns:
        True if trading day, False otherwise
    """
    # Check weekend
    if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Check holiday
    holidays = _parse_holiday_dates(date.year)
    if date in holidays:
        return False
    
    return True


def next_trading_day(date: datetime.date) -> datetime.date:
    """
    Get the next trading day after the given date.
    
    Args:
        date: Reference date
        
    Returns:
        Next trading day
    """
    next_day = date + datetime.timedelta(days=1)
    while not is_trading_day(next_day):
        next_day += datetime.timedelta(days=1)
    return next_day


def prev_trading_day(date: datetime.date) -> datetime.date:
    """
    Get the previous trading day before the given date.
    
    Args:
        date: Reference date
        
    Returns:
        Previous trading day
    """
    prev_day = date - datetime.timedelta(days=1)
    while not is_trading_day(prev_day):
        prev_day -= datetime.timedelta(days=1)
    return prev_day


def get_trading_days(start: datetime.date, end: datetime.date) -> List[datetime.date]:
    """
    Get all trading days between start and end dates (inclusive).
    
    Args:
        start: Start date
        end: End date
        
    Returns:
        List of trading days
    """
    trading_days = []
    current = start
    while current <= end:
        if is_trading_day(current):
            trading_days.append(current)
        current += datetime.timedelta(days=1)
    return trading_days


def is_market_open(now: Optional[datetime.datetime] = None) -> bool:
    """
    Check if the market is currently open.
    
    Market is open:
    - On trading days
    - Between 09:15 and 15:30 IST
    
    Args:
        now: Optional datetime to check (defaults to current time)
        
    Returns:
        True if market is open
    """
    if now is None:
        now = datetime.datetime.now(IST)
    
    # Convert to IST if not already
    if now.tzinfo is None:
        now = IST.localize(now)
    else:
        now = now.astimezone(IST)
    
    # Check if trading day
    if not is_trading_day(now.date()):
        return False
    
    # Check market hours
    current_time = now.time()
    return MARKET_OPEN_TIME <= current_time <= MARKET_CLOSE_TIME


def minutes_to_market_open(now: Optional[datetime.datetime] = None) -> int:
    """
    Get minutes until next market open.
    
    Returns negative number if market is currently open.
    
    Args:
        now: Optional datetime (defaults to current time)
        
    Returns:
        Minutes until market open (negative if open)
    """
    if now is None:
        now = datetime.datetime.now(IST)
    
    # Convert to IST if not already
    if now.tzinfo is None:
        now = IST.localize(now)
    else:
        now = now.astimezone(IST)
    
    current_date = now.date()
    current_time = now.time()
    
    # If market is open today
    if is_trading_day(current_date):
        # If before market open
        if current_time < MARKET_OPEN_TIME:
            open_datetime = datetime.datetime.combine(current_date, MARKET_OPEN_TIME)
            open_datetime = IST.localize(open_datetime)
            diff = open_datetime - now
            return int(diff.total_seconds() / 60)
        # If during market hours
        elif current_time <= MARKET_CLOSE_TIME:
            return -int((datetime.datetime.combine(current_date, MARKET_CLOSE_TIME) - 
                        datetime.datetime.combine(current_date, current_time)).total_seconds() / 60)
    
    # Find next trading day
    next_day = next_trading_day(current_date)
    open_datetime = datetime.datetime.combine(next_day, MARKET_OPEN_TIME)
    open_datetime = IST.localize(open_datetime)
    
    # Handle timezone for now
    if now.tzinfo is None:
        now = IST.localize(now)
    
    diff = open_datetime - now
    return int(diff.total_seconds() / 60)


def get_this_week_trading_days(now: Optional[datetime.date] = None) -> List[datetime.date]:
    """
    Get all trading days for the current week (Monday to Friday).
    
    Args:
        now: Optional reference date (defaults to today)
        
    Returns:
        List of trading days this week
    """
    if now is None:
        now = datetime.date.today()
    
    # Find Monday of this week
    monday = now - datetime.timedelta(days=now.weekday())
    
    # Get all days from Monday to Friday
    week_days = [monday + datetime.timedelta(days=i) for i in range(5)]
    
    # Filter to trading days only
    return [d for d in week_days if is_trading_day(d)]


def get_market_status_message(now: Optional[datetime.datetime] = None) -> str:
    """
    Get a human-readable market status message.
    
    Args:
        now: Optional datetime (defaults to current time)
        
    Returns:
        Status message
    """
    if now is None:
        now = datetime.datetime.now(IST)
    
    # Convert to IST
    if now.tzinfo is None:
        now = IST.localize(now)
    else:
        now = now.astimezone(IST)
    
    if is_market_open(now):
        mins_to_close = int((datetime.datetime.combine(now.date(), MARKET_CLOSE_TIME) - 
                             now.replace(tzinfo=None)).total_seconds() / 60)
        return f"Market OPEN — closes in {mins_to_close} minutes"
    
    if not is_trading_day(now.date()):
        next_day = next_trading_day(now.date())
        return f"Market CLOSED — holiday today, next trading day: {next_day}"
    
    mins_to_open = minutes_to_market_open(now)
    if mins_to_open > 0:
        hours = mins_to_open // 60
        mins = mins_to_open % 60
        if hours > 0:
            return f"Market CLOSED — opens in {hours}h {mins}m"
        return f"Market CLOSED — opens in {mins}m"
    
    next_day = next_trading_day(now.date())
    return f"Market CLOSED — next session: {next_day} at 09:15 IST"


if __name__ == "__main__":
    # Test the module
    today = datetime.date.today()
    print(f"Today: {today}")
    print(f"Is trading day: {is_trading_day(today)}")
    print(f"Next trading day: {next_trading_day(today)}")
    print(f"Previous trading day: {prev_trading_day(today)}")
    print(f"Market open: {is_market_open()}")
    print(f"Minutes to market open: {minutes_to_market_open()}")
    print(f"This week trading days: {get_this_week_trading_days()}")
    print(f"Status: {get_market_status_message()}")
