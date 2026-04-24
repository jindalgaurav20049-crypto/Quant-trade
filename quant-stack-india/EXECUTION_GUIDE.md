# Execution Guide — quant-stack-india

> Complete ground-zero setup guide for algorithmic trading on NSE/BSE

---

## 0. Prerequisites

### Python 3.11+

**Windows (winget):**
```powershell
winget install Python.Python.3.11
```

**macOS (Homebrew):**
```bash
brew install python@3.11
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-pip
```

**Verify installation:**
```bash
python3 --version  # Should show 3.11.x
```

### Git

**Windows:**
```powershell
winget install Git.Git
```

**macOS:**
```bash
brew install git
```

**Linux:**
```bash
sudo apt install git
```

### VS Code (Recommended)

Download from [code.visualstudio.com](https://code.visualstudio.com/)

Recommended extensions:
- Python (Microsoft)
- Pylance
- Python Docstring Generator
- YAML

---

## 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/yourusername/quant-stack-india.git
cd quant-stack-india

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate

# Install dependencies (takes 8-12 minutes)
pip install -r requirements.txt
```

**Note:** The installation includes PyTorch (~800MB download). On slow connections, this may take longer.

---

## 2. Validate Installation

```bash
python utils/validate_setup.py
```

**Expected output:**
```
✓ Python 3.11.7
✓ All 29 packages importable
✓ .env file: 12/12 variables set
✓ yfinance: RELIANCE.NS — 5 rows fetched
✓ nsepython: connected
✓ SQLite: writable
✓ READY TO TRADE
```

**Understanding check results:**

| Symbol | Meaning |
|--------|---------|
| ✓ Green | Check passed |
| ✗ Red | Check failed — see fix below |
| ⚠ Yellow | Warning — non-critical |

**Common failures and fixes:**

| Failure | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'x'` | Run `pip install x` or reinstall requirements |
| `.env file not found` | Run `cp .env.example .env` and fill in values |
| `yfinance: Connection error` | Check internet connection, try again |
| `nsepython: ConnectionError` | NSE website may be down, try again later |
| `SQLite: not writable` | Run `chmod 755 data/` or check disk space |

---

## 3. API Keys Setup

### Create .env file

```bash
cp .env.example .env
```

Edit `.env` with your favorite editor:

```bash
# Windows
notepad .env

# macOS/Linux
nano .env  # or vim, code, etc.
```

### API Key Reference

| Service | Where to Get | Cost | Required For |
|---------|--------------|------|--------------|
| **Zerodha API Key** | [kite.trade](https://kite.trade/) → Create App | ₹0 (Personal) | Live trading |
| **Zerodha API Secret** | Same as above | ₹0 | Live trading |
| **Zerodha TOTP Secret** | Kite 2FA setup | ₹0 | Auto login |
| **Angel API Key** | [smartapi.angelbroking.com](https://smartapi.angelbroking.com/) | ₹0 | Fallback broker |
| **FRED API Key** | [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) | ₹0 | Macro data |
| **Telegram Bot Token** | @BotFather on Telegram | ₹0 | Alerts |
| **Telegram Chat ID** | @userinfobot on Telegram | ₹0 | Alerts |

### Zerodha Setup (Primary Broker)

1. **Create Kite Account:**
   - Visit [kite.zerodha.com](https://kite.zerodha.com/)
   - Complete KYC if not already done

2. **Create Developer App:**
   - Go to [kite.trade](https://kite.trade/)
   - Click "Create App"
   - Select "Personal" app type (free for order placement)
   - Copy API Key and API Secret to `.env`

3. **Get TOTP Secret (CRITICAL):**
   - Login to Kite
   - Go to Account → Security → Enable 2FA
   - Select "Authenticator App"
   - **IMPORTANT:** When the QR code appears, click "Can't scan?"
   - Copy the **secret key** shown (starts with letters/numbers)
   - This is your `ZERODHA_TOTP_SECRET` — save it immediately!
   - ⚠️ This secret is shown **ONCE** during setup

4. **Test TOTP:**
   ```bash
   python -c "import pyotp; print(pyotp.TOTP('YOUR_SECRET').now())"
   ```
   Should print a 6-digit code that matches your authenticator app.

### Angel One Setup (Fallback Broker)

1. Visit [smartapi.angelbroking.com](https://smartapi.angelbroking.com/)
2. Create an app
3. Copy API Key, Client ID to `.env`
4. Use your MPIN as password

### FRED API Setup (Macro Data)

1. Visit [fred.stlouisfed.org](https://fred.stlouisfed.org/)
2. Create free account
3. Go to "My Account" → "API Keys"
4. Request API key (instant approval)
5. Copy to `.env` as `FRED_API_KEY`

### Telegram Bot Setup (Alerts)

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`
3. Follow prompts, choose name and username
4. Copy the **token** provided to `.env` as `TELEGRAM_BOT_TOKEN`
5. Message [@userinfobot](https://t.me/userinfobot)
6. Copy your **ID number** to `.env` as `TELEGRAM_CHAT_ID`

---

## 4. Zerodha Token Management

### Understanding Access Tokens

Zerodha access tokens expire at **midnight IST every day**. You must generate a fresh token each trading day.

### Automated Token Refresh (Recommended)

The scheduler handles this automatically at 08:00 IST:

```bash
python automation/scheduler.py
```

### Manual Token Refresh

If automation fails, refresh manually:

1. **Get request_token:**
   - Open: `https://kite.trade/connect/login?api_key=YOUR_API_KEY`
   - Login with your Kite credentials
   - After login, you'll be redirected to a URL like:
     ```
     https://127.0.0.1/?request_token=xyz123&action=login&status=success
     ```
   - Copy the `request_token` value (xyz123)

2. **Generate access token:**
   ```bash
   python automation/token_refresh.py --request-token xyz123
   ```

3. **Verify token saved:**
   ```bash
   cat .zerodha_token.json
   ```
   Should show today's date and access token.

---

## 5. Paper Trading First

### Configure Paper Mode

Edit `.env`:
```bash
TRADING_MODE=paper
```

### Run Validation

```bash
python utils/validate_setup.py
```

### Run Pipeline (Force on Non-Trading Day)

```bash
python automation/pipeline.py --mode paper --force
```

**Expected output:**
```
=== Pipeline starting at 2024-01-15 14:30:45 IST ===
Mode: PAPER
✓ Validation passed
✓ Broker initialized: zerodha (paper mode)
✓ Fetched data for 48/55 tickers
✓ India VIX: 14.52
✓ Price matrix: 252 days x 48 tickers
✓ Momentum signals: 10 positions
✓ Orders to place: 10
[PAPER] BUY 50 RELIANCE (CNC) — order_id: PAPER_RELIANCE_BUY_1705318245
[PAPER] BUY 30 TCS (CNC) — order_id: PAPER_TCS_BUY_1705318246
...
=== Pipeline complete: 10 orders placed ===
```

### Check Paper Orders

```bash
cat logs/pipeline.log
```

Paper orders are logged but NOT sent to the exchange.

---

## 6. Running Strategies Independently

### Test Momentum Factor Strategy

```bash
python -c "
from strategies.momentum.momentum_factor_portfolio import MomentumFactorPortfolio
print('Momentum Factor Portfolio loaded successfully')
"
```

### Test Volatility Targeting

```bash
python -c "
from strategies.volatility.volatility_targeting import VolatilityTargeting
vt = VolatilityTargeting(vol_target=0.15)
print(f'Volatility Targeting initialized: target={vt.vol_target}')
"
```

### Run Full Backtest

```bash
python backtesting/vectorbt_engine.py
```

### Launch Dashboard

```bash
streamlit run dashboard/streamlit_app.py
```

Then open: http://localhost:8501

---

## 7. Full Automated Pipeline

### Start Scheduler

```bash
python automation/scheduler.py
```

**What runs automatically:**

| IST Time | Job | Action |
|----------|-----|--------|
| 08:00 | Token Refresh | Generate fresh Zerodha token |
| 09:20 (Mon-Fri) | Trading Pipeline | Full signal → risk → execute flow |
| 15:45 (Mon-Fri) | EOD Reconciliation | Log positions, P&L |

### Monitor Scheduler

```bash
# In another terminal
tail -f logs/scheduler.log
```

### Stop Scheduler

Press `Ctrl+C` or send SIGTERM:
```bash
pkill -f scheduler.py
```

---

## 8. NSE-Specific Notes

### T+1 Settlement

- **Buy today**: Shares credited to demat next trading day
- **Sell today**: Funds available for withdrawal next trading day
- **Intraday**: Same-day settlement for MIS orders

### Product Types

| Type | Description | Square-off |
|------|-------------|------------|
| **CNC** | Cash & Carry (delivery) | No auto square-off |
| **MIS** | Margin Intraday Square-off | 15:20 IST auto square-off |
| **NRML** | Normal (F&O overnight) | No auto square-off |

### Circuit Bands

| Group | Band | Examples |
|-------|------|----------|
| A-group | ±20% | Nifty 50 stocks |
| B-group | ±10% | Mid-cap stocks |
| T-group | ±5% | Trade-to-trade |

The pipeline pre-validates orders against circuit limits.

### India VIX Safety Rules

| VIX Level | Action |
|-----------|--------|
| < 15 | Full exposure |
| 15-20 | Normal exposure |
| 20-25 | Reduce to 75% |
| 25-30 | Reduce to 50% |
| > 30 | **HALT** — no new positions |

### SEBI Registration

Retail algorithms under **10 orders/second** do not require SEBI registration. This framework typically generates <5 orders per run.

---

## 9. Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `nsepython ConnectionError` | NSE website down | Try again in 5 minutes |
| `Zerodha 403 Forbidden` | Invalid/expired token | Run token_refresh.py |
| `yfinance empty DataFrame` | Ticker delisted/wrong suffix | Check ticker symbol |
| `vectorbt numba error` | Numba version mismatch | `pip install numba==0.58.1` |
| `TOTP invalid` | Clock sync issue | Sync system time to NTP |
| `Port 8501 in use` | Another Streamlit running | `pkill -f streamlit` |
| `ModuleNotFoundError: pandas_ta` | Package not installed | `pip install pandas-ta==0.3.14b0` |
| `kiteconnect import error` | KiteConnect not installed | `pip install kiteconnect==5.0.1` |
| `SQLite database locked` | Concurrent access | Close other processes |
| `APScheduler timezone error` | pytz not installed | `pip install pytz==2024.1` |
| `torch CUDA error` | GPU mismatch | `pip install torch==2.2.0+cpu` |
| `smartapi import error` | SmartAPI not installed | `pip install smartapi-python==1.3.9` |
| `FRED API error` | Invalid API key | Check FRED_API_KEY in .env |
| `Telegram bot not responding` | Wrong chat ID | Verify with @userinfobot |
| `Circuit breaker rejection` | Order outside band | Check prev_close and circuit limit |

### Debug Mode

Enable verbose logging:

```bash
export LOG_LEVEL=DEBUG  # Windows: set LOG_LEVEL=DEBUG
python automation/pipeline.py --mode paper --force
```

### Reset Everything

```bash
# Clean up all generated files
rm -rf logs/*.log
rm -rf data/*.db
rm -f .zerodha_token.json
rm -rf __pycache__ */__pycache__ */*/__pycache__

# Re-validate
python utils/validate_setup.py
```

---

## 10. SEBI Compliance Reminder

### For Personal/Educational Use

This framework is designed for:
- Personal algorithmic trading
- Educational purposes
- Strategy research and backtesting

### Before Going Live

1. **Paper trade for at least 1 month**
2. **Start with small capital** (₹1L or less)
3. **Keep max drawdown at 15%** (configurable in settings.yaml)
4. **Review all orders** before market open
5. **Monitor first few runs manually**

### Risk Limits (Recommended)

Edit `config/settings.yaml`:
```yaml
risk:
  max_position_size: 0.10        # Max 10% in single stock
  max_portfolio_drawdown: 0.15   # Halt at 15% DD
  volatility_target_annual: 0.15 # 15% vol target
```

### Not Financial Advice

This software is provided for educational purposes only. Always:
- Consult a SEBI-registered investment advisor
- Do your own research
- Understand the risks of algorithmic trading

---

## Next Steps

1. ✅ Complete setup (this guide)
2. 📊 Read [STRATEGY_GUIDE.md](STRATEGY_GUIDE.md) for strategy details
3. 📈 Paper trade for 1 month
4. 🚀 Go live with small capital
5. 📉 Monitor and adjust

**Happy trading! 🇮🇳**

---

*For support, open an issue on GitHub or contact the maintainers.*
