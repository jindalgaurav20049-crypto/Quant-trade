"""
Telegram Alert Module

Sends notifications via Telegram Bot API.
"""

import os
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def get_telegram_credentials() -> tuple:
    """Get Telegram credentials from environment."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    return bot_token, chat_id


def send_telegram_message(message: str) -> bool:
    """
    Send a message via Telegram.
    
    Args:
        message: Message text
        
    Returns:
        True if successful
    """
    bot_token, chat_id = get_telegram_credentials()
    
    if not bot_token or bot_token == "your_bot_token_here":
        logger.debug("Telegram bot token not set — skipping alert")
        return False
    
    if not chat_id:
        logger.debug("Telegram chat ID not set — skipping alert")
        return False
    
    try:
        import requests
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info("Telegram alert sent successfully")
            return True
        else:
            logger.error(f"Telegram API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
        return False


def send_pipeline_summary(
    orders: List[dict],
    portfolio_value: float,
    india_vix: Optional[float],
    mode: str
) -> bool:
    """
    Send pipeline execution summary.
    
    Args:
        orders: List of placed orders
        portfolio_value: Portfolio value
        india_vix: India VIX value
        mode: Trading mode
        
    Returns:
        True if successful
    """
    message = f"""
📊 *quant-stack India — Pipeline Summary*

Mode: {mode.upper()}
Portfolio Value: ₹{portfolio_value:,.0f}
India VIX: {india_vix:.2f if india_vix else 'N/A'}
Orders Placed: {len(orders)}

*Orders:*
"""
    
    for order in orders[:10]:  # Show first 10 orders
        emoji = "🟢" if order["side"] == "BUY" else "🔴"
        message += f"{emoji} {order['side']} {order['qty']} {order['ticker']}\n"
    
    if len(orders) > 10:
        message += f"... and {len(orders) - 10} more orders\n"
    
    return send_telegram_message(message)


def send_risk_alert(
    alert_type: str,
    message: str,
    portfolio_value: Optional[float] = None
) -> bool:
    """
    Send risk alert.
    
    Args:
        alert_type: Type of risk alert
        message: Alert message
        portfolio_value: Optional portfolio value
        
    Returns:
        True if successful
    """
    emoji = "⚠️" if alert_type == "warning" else "🚨"
    
    telegram_msg = f"""
{emoji} *RISK ALERT: {alert_type.upper()}*

{message}
"""
    
    if portfolio_value:
        telegram_msg += f"\nPortfolio Value: ₹{portfolio_value:,.0f}"
    
    return send_telegram_message(telegram_msg)


def send_trade_alert(
    ticker: str,
    side: str,
    qty: int,
    price: float,
    order_id: str
) -> bool:
    """
    Send trade execution alert.
    
    Args:
        ticker: Stock symbol
        side: "BUY" or "SELL"
        qty: Quantity
        price: Execution price
        order_id: Order ID
        
    Returns:
        True if successful
    """
    emoji = "🟢 BUY" if side == "BUY" else "🔴 SELL"
    
    message = f"""
💼 *Trade Executed*

{emoji} {qty} {ticker} @ ₹{price:.2f}
Order ID: `{order_id}`
Value: ₹{qty * price:,.2f}
"""
    
    return send_telegram_message(message)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test Telegram Alerts ===")
    
    # Test pipeline summary
    test_orders = [
        {"ticker": "RELIANCE", "qty": 10, "side": "BUY"},
        {"ticker": "TCS", "qty": 5, "side": "BUY"},
    ]
    send_pipeline_summary(test_orders, 1000000, 15.5, "paper")
    
    # Test risk alert
    send_risk_alert("warning", "Drawdown approaching limit", 850000)
    
    # Test trade alert
    send_trade_alert("RELIANCE", "BUY", 10, 2500, "PAPER_12345")
