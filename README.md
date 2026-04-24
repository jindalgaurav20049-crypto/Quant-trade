# quant-stack-india ☸

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![NSE](https://img.shields.io/badge/NSE-India-green.svg)](https://www.nseindia.com/)
[![BSE](https://img.shields.io/badge/BSE-India-orange.svg)](https://www.bseindia.com/)

> A production-grade algorithmic trading framework for Indian capital markets (NSE/BSE). Built for retail quants, by quants.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         QUANT-STACK INDIA ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│   │   YFinance  │    │  nsepython  │    │  jugaad-    │    │    FRED     │  │
│   │   (.NS/.BO) │    │  (Live NSE) │    │    data     │    │   (Macro)   │  │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘  │
│          └───────────────────┴───────────────────┴───────────────────┘       │
│                              │                                               │
│                    ┌─────────┴─────────┐                                     │
│                    │  Data Pipeline    │                                     │
│                    │  (OHLCV + India   │                                     │
│                    │   VIX + FII/DII)  │                                     │
│                    └─────────┬─────────┘                                     │
│                              │                                               │
│   ┌──────────────────────────┼──────────────────────────┐                   │
│   │                          │                          │                   │
│   ▼                          ▼                          ▼                   │
│ ┌──────────────┐    ┌────────────────┐    ┌────────────────────┐           │
│ │   MOMENTUM   │    │ MEAN REVERSION │    │  VOLATILITY        │           │
│ │  12-1 Factor │    │ Pairs Trading  │    │  Targeting (15%)   │           │
│ │  Portfolio   │    │ Bollinger Bands│    │  VIX Regime Filter │           │
│ └──────┬───────┘    └───────┬────────┘    └─────────┬──────────┘           │
│        │                    │                       │                       │
│        └────────────────────┼───────────────────────┘                       │
│                             │                                               │
│                    ┌────────┴────────┐                                      │
│                    │  Risk Engine    │                                      │
│                    │ • Circuit Bands │                                      │
│                    │ • Position Size │                                      │
│                    │ • Vol Overlay   │                                      │
│                    └────────┬────────┘                                      │
│                             │                                               │
│        ┌────────────────────┼────────────────────┐                         │
│        │                    │                    │                         │
│        ▼                    ▼                    ▼                         │
│   ┌─────────┐         ┌─────────┐         ┌─────────┐                      │
│   │ Zerodha │         │  Angel  │         │  Fyers  │                      │
│   │  Kite   │         │ SmartAPI│         │  APIv3  │                      │
│   └─────────┘         └─────────┘         └─────────┘                      │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    Streamlit Dashboard (IST)                       │   │
│   │  • INR Formatting • India VIX Gauge • FII/DII Flows • P&L Tracker │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Features

### India-Specific Design
- **NSE/BSE tickers**: Automatic `.NS`/`.BO` suffix handling
- **IST timezone**: All timestamps in Asia/Kolkata
- **Indian tax calculator**: STT, STCG/LTCG, GST, stamp duty
- **Circuit breaker awareness**: ±5/10/20% NSE bands
- **F&O lot sizes**: Built-in NIFTY (75), BANKNIFTY (30), FINNIFTY (65)

### Strategies Included
| Strategy | Description | Expected Vol |
|----------|-------------|--------------|
| Momentum Factor (12-1) | Cross-sectional momentum on Nifty 500 | 15-18% |
| Volatility Targeting | Dynamic leverage to hit 15% vol target | 15% |
| Pairs Trading | Cointegration-based (HDFCBANK/ICICIBANK, TCS/INFY) | 8-12% |
| Bollinger Reversion | Mean reversion with BBands | 12-15% |
| FII/DII Flow | Institutional flow following | 10-14% |
| Quality-Value | P/E, P/B, ROE factor scoring | 12-16% |

### Risk Management
- **Volatility targeting**: 15% annualized target with EWMA
- **India VIX regime filter**: Reduce exposure when VIX > 20, halt when > 30
- **Circuit breaker pre-check**: Validate orders before sending to NSE
- **Position sizing**: Kelly criterion, fixed fractional, vol-scaled
- **Max drawdown halt**: Stop trading at 15% portfolio DD

### Broker Integrations
- **Zerodha KiteConnect** (primary): Full TOTP automation
- **Angel One SmartAPI** (fallback): Free API access
- **Fyers API v3** (fallback): Modern REST API
- **Paper trading mode**: Simulate all orders locally

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/yourusername/quant-stack-india.git
cd quant-stack-india

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies (takes 8-12 minutes)
pip install -r requirements.txt

# 4. Setup environment
cp .env.example .env
# Edit .env with your API keys

# 5. Validate installation
python utils/validate_setup.py

# 6. Run paper trading pipeline
python automation/pipeline.py --mode paper --force

# 7. Launch dashboard
streamlit run dashboard/streamlit_app.py
```

## Project Structure

```
quant-stack-india/
├── README.md                 # This file
├── EXECUTION_GUIDE.md        # Complete setup guide
├── STRATEGY_GUIDE.md         # Strategy deep-dives
├── requirements.txt          # Pinned dependencies
├── .env.example              # Environment template
├── config/
│   └── settings.yaml         # Universe, risk params
├── utils/
│   ├── validate_setup.py     # Pre-flight checks
│   ├── nse_calendar.py       # NSE holidays + market hours
│   ├── indian_tax.py         # STT, STCG/LTCG calculator
│   └── logger.py             # Centralized logging
├── data/
│   ├── fetchers/             # yfinance, nsepython, FRED
│   ├── processors/           # Cleaner, feature engineer
│   └── storage/              # SQLite store
├── strategies/
│   ├── momentum/             # 12-1 factor, cross-sectional
│   ├── mean_reversion/       # Pairs, Bollinger
│   ├── volatility/           # Vol targeting, VIX regime
│   ├── factor/               # Quality-value, FII/DII
│   └── ml_based/             # Random Forest classifier
├── backtesting/
│   ├── vectorbt_engine.py    # Primary backtest engine
│   ├── walk_forward.py       # IS/OOS optimization
│   └── results/              # Performance reports
├── risk/
│   ├── position_sizer.py     # Kelly, vol-scaled sizing
│   ├── circuit_breakers.py   # NSE circuit validation
│   └── risk_monitor.py       # Live risk tracking
├── execution/
│   ├── brokers/              # Zerodha, Angel, Fyers
│   ├── order_manager.py      # Order routing
│   └── transaction_costs.py  # Full cost model
├── automation/
│   ├── scheduler.py          # APScheduler (IST)
│   ├── pipeline.py           # Full trading pipeline
│   ├── token_refresh.py      # Zerodha TOTP automation
│   └── alerts/               # Telegram notifications
├── dashboard/
│   ├── streamlit_app.py      # Main dashboard
│   └── plotly_charts.py      # INR-formatted charts
└── tests/                    # Unit tests
```

## Daily Schedule (IST)

| Time | Job | Description |
|------|-----|-------------|
| 08:00 | Token Refresh | Zerodha TOTP login |
| 09:10 | Pre-Market Check | Data validation, margin check |
| 09:20 | Trading Pipeline | Signals → Risk → Execution |
| 15:45 | EOD Reconciliation | P&L, positions, logs |

## API Costs

| Service | Cost | Notes |
|---------|------|-------|
| Zerodha Personal API | ₹0 | For order placement |
| Zerodha Live Data | ₹500/mo | Optional (yfinance free) |
| Angel SmartAPI | ₹0 | Free fallback broker |
| FRED API | ₹0 | Free macro data |
| Telegram Bot | ₹0 | Free alerts |

## Performance Expectations

Based on backtests (2015-2024, gross of costs):

| Strategy | CAGR | Sharpe | Max DD |
|----------|------|--------|--------|
| Momentum Factor | 18-22% | 1.1-1.3 | -18% |
| Vol Targeting Overlay | +2-4% | +0.15 | -2% |
| Pairs Trading | 12-16% | 1.2-1.5 | -8% |
| Bollinger Reversion | 14-18% | 1.0-1.2 | -15% |

*Past performance does not guarantee future results. Always paper trade first.*

## SEBI Compliance

- This framework is for **personal/educational use only**
- Retail algos under 10 orders/sec do not require SEBI registration
- Always start with `TRADING_MODE=paper`
- Keep `risk.max_portfolio_drawdown` at 0.15 (15%)
- Not financial advice — consult a SEBI-registered advisor

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License — see [LICENSE](LICENSE) for details.

## Disclaimer

Trading in Indian securities involves substantial risk of loss. This software is provided "as is" without warranty of any kind. The authors assume no liability for trading losses incurred using this framework. Always paper trade extensively before deploying live capital.

---

**Built with ❤️ for the Indian quant community**

*For detailed setup instructions, see [EXECUTION_GUIDE.md](EXECUTION_GUIDE.md)*  
*For strategy documentation, see [STRATEGY_GUIDE.md](STRATEGY_GUIDE.md)*
