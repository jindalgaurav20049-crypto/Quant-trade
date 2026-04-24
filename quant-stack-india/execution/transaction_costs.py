"""
Transaction Cost Calculator

Full Indian brokerage cost model including STT, GST, SEBI charges, etc.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class TransactionCostCalculator:
    """
    Calculate all-in transaction costs for Indian equity trades.
    """
    
    def __init__(self):
        # Brokerage rates (Zerodha model)
        self.delivery_brokerage = 0.0
        self.intraday_brokerage_rate = 0.0003
        self.intraday_brokerage_max = 20.0
        
        # STT rates
        self.stt_delivery = 0.001  # 0.1%
        self.stt_intraday_sell = 0.00025  # 0.025%
        
        # Exchange transaction charge
        self.exchange_charge_rate = 0.0000322  # 0.00322%
        
        # SEBI charge
        self.sebi_charge_rate = 0.000001  # ₹10 per crore
        
        # GST
        self.gst_rate = 0.18
        
        # Stamp duty
        self.stamp_duty_delivery = 0.00015  # 0.015%
        self.stamp_duty_intraday = 0.00003  # 0.003%
    
    def calculate(
        self,
        ticker: str,
        qty: int,
        price: float,
        side: str,
        product: str
    ) -> Dict:
        """
        Calculate transaction costs.
        
        Args:
            ticker: Stock symbol
            qty: Quantity
            price: Price per share
            side: "BUY" or "SELL"
            product: "CNC", "MIS", or "NRML"
            
        Returns:
            Dictionary with cost breakdown
        """
        turnover = qty * price
        
        # Brokerage
        if product == "CNC":
            brokerage = self.delivery_brokerage
        else:
            brokerage = min(
                self.intraday_brokerage_max,
                self.intraday_brokerage_rate * turnover
            )
        
        # STT
        if product == "CNC":
            stt = self.stt_delivery * turnover
        else:
            stt = self.stt_intraday_sell * turnover if side == "SELL" else 0.0
        
        # Exchange transaction charge
        exchange_charge = self.exchange_charge_rate * turnover
        
        # SEBI charge
        sebi_charge = self.sebi_charge_rate * turnover
        
        # GST
        gst = self.gst_rate * (brokerage + exchange_charge)
        
        # Stamp duty
        if side == "BUY":
            if product == "CNC":
                stamp_duty = self.stamp_duty_delivery * turnover
            else:
                stamp_duty = self.stamp_duty_intraday * turnover
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
    
    def calculate_round_trip(
        self,
        ticker: str,
        qty: int,
        entry_price: float,
        exit_price: float,
        product: str = "CNC"
    ) -> Dict:
        """
        Calculate costs for a round-trip trade.
        
        Args:
            ticker: Stock symbol
            qty: Quantity
            entry_price: Entry price
            exit_price: Exit price
            product: Product type
            
        Returns:
            Dictionary with combined costs
        """
        buy_costs = self.calculate(ticker, qty, entry_price, "BUY", product)
        sell_costs = self.calculate(ticker, qty, exit_price, "SELL", product)
        
        gross_pnl = (exit_price - entry_price) * qty
        total_costs = buy_costs['total_cost'] + sell_costs['total_cost']
        net_pnl = gross_pnl - total_costs
        
        return {
            'buy_costs': buy_costs,
            'sell_costs': sell_costs,
            'gross_pnl': round(gross_pnl, 2),
            'total_costs': round(total_costs, 4),
            'net_pnl': round(net_pnl, 2),
            'cost_pct_of_pnl': round((total_costs / abs(gross_pnl)) * 100, 4) if gross_pnl != 0 else 0.0
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test TransactionCostCalculator ===")
    calculator = TransactionCostCalculator()
    
    costs = calculator.calculate("RELIANCE.NS", 100, 2500, "BUY", "CNC")
    print(f"Buy 100 RELIANCE @ ₹2500:")
    for key, value in costs.items():
        print(f"  {key}: {value}")
    
    print("\n=== Test round-trip ===")
    round_trip = calculator.calculate_round_trip("RELIANCE.NS", 100, 2500, 2600, "CNC")
    print(f"Round-trip P&L:")
    print(f"  Gross: ₹{round_trip['gross_pnl']}")
    print(f"  Costs: ₹{round_trip['total_costs']}")
    print(f"  Net: ₹{round_trip['net_pnl']}")
