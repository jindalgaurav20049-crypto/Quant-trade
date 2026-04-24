"""
Indian Equity Transaction Cost and Tax Calculator

Calculates all-in costs for trading on NSE/BSE including:
- Brokerage (Zerodha model)
- STT (Securities Transaction Tax)
- Exchange transaction charges
- GST
- SEBI charges
- Stamp duty
- STCG/LTCG taxes
"""

from typing import Dict


def calculate_transaction_costs(
    ticker: str,
    qty: int,
    price: float,
    side: str,
    product: str
) -> Dict[str, float]:
    """
    Calculate all-in costs for an Indian equity trade.
    
    Args:
        ticker: Stock symbol (e.g., "RELIANCE.NS")
        qty: Number of shares
        price: Price per share
        side: "BUY" or "SELL"
        product: "CNC" (delivery), "MIS" (intraday), or "NRML" (F&O)
        
    Returns:
        Dictionary with cost breakdown:
        - brokerage: Brokerage fee
        - stt: Securities Transaction Tax
        - exchange_txn_charge: NSE/BSE transaction charge
        - gst: GST on brokerage + exchange charges
        - sebi_charge: SEBI turnover fee
        - stamp_duty: Stamp duty (buy only)
        - total_cost: Total transaction cost
        - total_pct: Total cost as percentage of turnover
        - turnover: Total trade value
    """
    turnover = qty * price
    
    # Brokerage (Zerodha model)
    if product == 'CNC':
        brokerage = 0.0  # Zerodha free delivery
    else:
        brokerage = min(20.0, 0.0003 * turnover)  # ₹20 flat or 0.03%
    
    # STT (Securities Transaction Tax)
    if side == 'BUY' and product == 'CNC':
        stt = 0.001 * turnover  # 0.1% on buy delivery
    elif side == 'SELL' and product == 'CNC':
        stt = 0.001 * turnover  # 0.1% on sell delivery
    elif product == 'MIS':
        stt = 0.00025 * turnover if side == 'SELL' else 0.0  # intraday only on sell
    else:
        stt = 0.0
    
    # Exchange transaction charge (NSE)
    exchange_charge = 0.0000322 * turnover  # NSE equity: 0.00322 bps
    
    # SEBI charges (₹10 per crore = 0.000001)
    sebi_charge = 0.000001 * turnover
    
    # GST on brokerage + exchange charges (18%)
    gst = 0.18 * (brokerage + exchange_charge)
    
    # Stamp duty (on buy side only, NSE equity)
    # 0.015% for delivery, 0.003% for intraday
    if side == 'BUY':
        if product == 'CNC':
            stamp_duty = 0.00015 * turnover
        elif product == 'MIS':
            stamp_duty = 0.00003 * turnover
        else:
            stamp_duty = 0.0
    else:
        stamp_duty = 0.0
    
    total_cost = brokerage + stt + exchange_charge + sebi_charge + gst + stamp_duty
    total_pct = (total_cost / turnover) * 100 if turnover > 0 else 0.0
    
    return {
        'brokerage': round(brokerage, 4),
        'stt': round(stt, 4),
        'exchange_txn_charge': round(exchange_charge, 4),
        'sebi_charge': round(sebi_charge, 4),
        'gst': round(gst, 4),
        'stamp_duty': round(stamp_duty, 4),
        'total_cost': round(total_cost, 4),
        'total_pct': round(total_pct, 6),
        'turnover': round(turnover, 2)
    }


def estimate_stcg_tax(profit: float) -> float:
    """
    Estimate Short-Term Capital Gains tax on Indian equity.
    
    STCG applies to equity held for less than 1 year.
    Rate: 20% (post August 2024 budget)
    
    Args:
        profit: Short-term capital gain (positive value)
        
    Returns:
        Estimated STCG tax
    """
    return max(0.0, profit * 0.20)


def estimate_ltcg_tax(profit: float) -> float:
    """
    Estimate Long-Term Capital Gains tax on Indian equity.
    
    LTCG applies to equity held for more than 1 year.
    Rate: 12.5% above ₹1.25L exemption (post August 2024 budget)
    
    Args:
        profit: Long-term capital gain (positive value)
        
    Returns:
        Estimated LTCG tax
    """
    exemption = 125000.0
    taxable = max(0.0, profit - exemption)
    return taxable * 0.125


def calculate_round_trip_costs(
    ticker: str,
    qty: int,
    entry_price: float,
    exit_price: float,
    product: str = "CNC"
) -> Dict[str, float]:
    """
    Calculate total costs for a round-trip trade (buy + sell).
    
    Args:
        ticker: Stock symbol
        qty: Number of shares
        entry_price: Entry price per share
        exit_price: Exit price per share
        product: "CNC", "MIS", or "NRML"
        
    Returns:
        Dictionary with combined buy and sell costs
    """
    buy_costs = calculate_transaction_costs(ticker, qty, entry_price, "BUY", product)
    sell_costs = calculate_transaction_costs(ticker, qty, exit_price, "SELL", product)
    
    gross_pnl = (exit_price - entry_price) * qty
    total_costs = buy_costs['total_cost'] + sell_costs['total_cost']
    net_pnl = gross_pnl - total_costs
    
    return {
        'buy_costs': buy_costs,
        'sell_costs': sell_costs,
        'gross_pnl': round(gross_pnl, 2),
        'total_costs': round(total_costs, 4),
        'net_pnl': round(net_pnl, 2),
        'cost_pct_of_pnl': round((total_costs / gross_pnl) * 100, 4) if gross_pnl != 0 else 0.0
    }


def get_tax_summary(
    stcg_profit: float = 0.0,
    ltcg_profit: float = 0.0,
    stcg_loss: float = 0.0,
    ltcg_loss: float = 0.0
) -> Dict[str, float]:
    """
    Get a summary of tax liability for the financial year.
    
    Args:
        stcg_profit: Total STCG profits
        ltcg_profit: Total LTCG profits
        stcg_loss: Total STCG losses (can offset STCG)
        ltcg_loss: Total LTCG losses (can offset LTCG)
        
    Returns:
        Tax summary dictionary
    """
    # Offset losses against gains
    net_stcg = max(0.0, stcg_profit - stcg_loss)
    net_ltcg = max(0.0, ltcg_profit - ltcg_loss)
    
    stcg_tax = estimate_stcg_tax(net_stcg)
    ltcg_tax = estimate_ltcg_tax(net_ltcg)
    
    return {
        'gross_stcg': stcg_profit,
        'gross_ltcg': ltcg_profit,
        'stcg_loss_offset': min(stcg_profit, stcg_loss),
        'ltcg_loss_offset': min(ltcg_profit, ltcg_loss),
        'net_stcg': net_stcg,
        'net_ltcg': net_ltcg,
        'stcg_tax': stcg_tax,
        'ltcg_tax': ltcg_tax,
        'total_tax': stcg_tax + ltcg_tax
    }


if __name__ == "__main__":
    # Example usage
    print("=== Transaction Cost Example ===")
    costs = calculate_transaction_costs("RELIANCE.NS", 100, 2500.0, "BUY", "CNC")
    print(f"Buy 100 RELIANCE @ ₹2500:")
    for key, value in costs.items():
        print(f"  {key}: {value}")
    
    print("\n=== Round-Trip Cost Example ===")
    round_trip = calculate_round_trip_costs("RELIANCE.NS", 100, 2500.0, 2600.0, "CNC")
    print(f"Buy 100 RELIANCE @ ₹2500, Sell @ ₹2600:")
    print(f"  Gross P&L: ₹{round_trip['gross_pnl']}")
    print(f"  Total Costs: ₹{round_trip['total_costs']}")
    print(f"  Net P&L: ₹{round_trip['net_pnl']}")
    
    print("\n=== Tax Example ===")
    tax_summary = get_tax_summary(
        stcg_profit=500000,
        ltcg_profit=300000,
        stcg_loss=50000,
        ltcg_loss=20000
    )
    print(f"Tax Summary:")
    for key, value in tax_summary.items():
        print(f"  {key}: ₹{value:,.2f}")
