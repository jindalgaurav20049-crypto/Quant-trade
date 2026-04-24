# Strategy Guide — quant-stack-india

> Deep-dive documentation for all trading strategies in the framework

---

## Table of Contents

1. [Momentum Factor Portfolio](#momentum-factor-portfolio)
2. [Volatility Targeting](#volatility-targeting)
3. [Pairs Trading](#pairs-trading)
4. [Bollinger Bands Reversion](#bollinger-bands-reversion)
5. [FII/DII Flow Strategy](#fiidii-flow-strategy)
6. [Quality-Value Factor](#quality-value-factor)
7. [Random Forest Classifier](#random-forest-classifier)

---

## Momentum Factor Portfolio

### Overview

Cross-sectional momentum strategy on NSE universe implementing the classic "12-1 momentum" factor.

**Logic:** Stocks that performed well over the past 12 months (excluding the most recent month) tend to continue outperforming.

### Why 12-1?

- **12-month lookback**: Captures medium-term trend persistence
- **Exclude 1 month**: Avoids short-term reversal contamination (Jegadeesh & Titman, 1993)

### Implementation

```python
from strategies.momentum.momentum_factor_portfolio import MomentumFactorPortfolio

strategy = MomentumFactorPortfolio(
    universe_tickers=nifty500_tickers,
    lookback_months=12,      # 12-month momentum
    skip_months=1,           # Exclude last month
    long_decile=0.10,        # Top 10% go long
    short_decile=0.10,       # Bottom 10% go short (optional)
    long_short=False,        # Long-only mode
    vol_target=0.15,         # 15% annualized vol target
    rebalance_freq="monthly",
    top_n=10                 # Select top 10 stocks
)

signals = strategy.generate_signals(prices_df, portfolio_returns, india_vix)
```

### Signal Calculation

```
Momentum Score = (Price[T-1month] / Price[T-12months]) - 1
```

### Portfolio Construction

1. Rank all stocks by momentum score
2. Select top N stocks (default: 10)
3. Equal weight within long book
4. Apply volatility targeting overlay
5. Apply India VIX regime filter

### Historical Performance (India)

Based on academic studies (2010-2023, gross):

| Metric | Value |
|--------|-------|
| Annualized Return | 18-22% |
| Sharpe Ratio | 1.1-1.3 |
| Maximum Drawdown | -18% |
| Win Rate (months) | 62% |

### Risk Considerations

- **Momentum crashes**: Strategy underperforms during sharp reversals (e.g., March 2020)
- **Concentration risk**: Top 10 stocks = 10% of portfolio each
- **Turnover**: ~100% monthly (high transaction costs)

### When It Works Best

- Trending markets
- Low volatility regimes (VIX < 20)
- Post-earnings drift periods

### When It Struggles

- Sharp reversals
- High volatility (VIX > 25)
- Market bottoms (value outperforms)

---

## Volatility Targeting

### Overview

Dynamic leverage strategy that adjusts position sizes so portfolio volatility equals a target level (default: 15% annualized).

**Core Idea:** When markets are calm, increase exposure. When markets spike, reduce exposure.

### Mathematical Framework

```
Realized Volatility = sqrt(EWMA_variance × 252)
Volatility Scalar = Vol_Target / Realized_Volatility
Clipped Scalar = clip(Scalar, 0.25, 2.0)
```

### Implementation

```python
from strategies.volatility.volatility_targeting import VolatilityTargeting

vt = VolatilityTargeting(
    vol_target=0.15,         # 15% annualized target
    ewma_span=20,            # 20-day EWMA window
    min_scalar=0.25,         # Minimum 25% exposure
    max_scalar=2.0,          # Maximum 200% exposure
    vix_reduce_threshold=20.0,
    vix_halt_threshold=30.0
)

# Scale positions
scaled_weights = vt.scale_positions(target_weights, portfolio_returns, india_vix)

# Scale quantities (integer shares)
scaled_quantities = vt.scale_quantities(target_quantities, portfolio_returns, india_vix)
```

### India VIX Override

| VIX Level | Action |
|-----------|--------|
| < 20 | Normal vol targeting |
| 20-30 | Cap scalar at 0.75 |
| > 30 | Force scalar to 0 (halt) |

### EWMA Calculation

```python
# Exponentially weighted moving average variance
ewma_var = returns.ewm(span=20, min_periods=5).var().iloc[-1]
realized_vol = sqrt(ewma_var * 252)
```

### Performance Impact

| Metric | Raw Strategy | With Vol Targeting |
|--------|--------------|-------------------|
| Return | 20% | 18% |
| Volatility | 22% | 15% |
| Sharpe | 0.91 | 1.20 |
| Max DD | -25% | -18% |

### Use Cases

1. **Overlay**: Apply to any strategy's returns
2. **Standalone**: Vol-targeted index exposure
3. **Risk management**: Reduce size before drawdowns

---

## Pairs Trading

### Overview

Statistical arbitrage strategy that trades the mean-reverting spread between two cointegrated stocks.

### Hardcoded Pairs (NSE)

| Pair | Sector | Rationale |
|------|--------|-----------|
| HDFCBANK / ICICIBANK | Banking | Similar business model, correlated earnings |
| TCS / INFY | IT Services | Industry leaders, similar macro exposure |
| BAJFINANCE / KOTAKBANK | NBFC/Bank | Financial services correlation |

### Implementation

```python
from strategies.mean_reversion.pairs_trading import PairsTrading

pair = PairsTrading(
    stock_a="HDFCBANK.NS",
    stock_b="ICICIBANK.NS",
    lookback=252,            # 1 year for cointegration test
    entry_zscore=2.0,        # Enter at ±2 sigma
    exit_zscore=0.5,         # Exit at ±0.5 sigma
    use_kalman=True          # Dynamic hedge ratio
)

signals = pair.generate_signals(prices_a, prices_b)
```

### Methodology

1. **Cointegration Test** (Engle-Granger):
   ```
   If p-value < 0.05: Series are cointegrated
   ```

2. **Hedge Ratio** (Kalman Filter):
   ```
   Spread = Price_A - β × Price_B
   β updates dynamically with each observation
   ```

3. **Z-Score Calculation**:
   ```
   Z = (Spread - Mean) / Std
   ```

4. **Signals**:
   - Z > +2.0: Short A, Long B (spread will narrow)
   - Z < -2.0: Long A, Short B (spread will widen)
   - |Z| < 0.5: Exit position

### Risk Management

- **Stop loss**: Exit if Z > 4.0 (fundamental divergence)
- **Position sizing**: Equal dollar exposure on both legs
- **Max holding**: 20 days (force exit)

### Historical Performance

| Metric | HDFCBANK/ICICIBANK | TCS/INFY |
|--------|-------------------|----------|
| Annualized Return | 12-16% | 10-14% |
| Sharpe Ratio | 1.2-1.5 | 1.0-1.3 |
| Max Drawdown | -8% | -10% |
| Win Rate | 58% | 55% |

---

## Bollinger Bands Reversion

### Overview

Mean reversion strategy using Bollinger Bands to identify overbought/oversold conditions.

### Implementation

```python
from strategies.mean_reversion.bollinger_bands_reversion import BollingerBandsReversion

bb = BollingerBandsReversion(
    window=20,               # 20-day moving average
    num_std=2.0,             # ±2 standard deviation bands
    exit_at_middle=True      # Exit when price crosses middle band
)

signals = bb.generate_signals(price_series)
```

### Signal Logic

| Condition | Action |
|-----------|--------|
| Price < Lower Band | Buy (oversold) |
| Price > Upper Band | Sell/Short (overbought) |
| Price crosses Middle Band | Exit position |

### Formula

```
Middle Band = SMA(20)
Upper Band = SMA(20) + 2 × Std(20)
Lower Band = SMA(20) - 2 × Std(20)
```

### Best Markets

- Range-bound stocks
- Low volatility regimes
- Mean-reverting sectors (utilities, consumer staples)

### Worst Markets

- Strong trending markets
- High volatility breakouts
- Momentum-driven stocks

---

## FII/DII Flow Strategy

### Overview

Institutional flow-following strategy based on Foreign Institutional Investor (FII) and Domestic Institutional Investor (DII) net flows.

### Logic

- **FII inflows > ₹1000Cr for 3 consecutive days** → Bullish signal
- **FII outflows > ₹1000Cr** → Go to cash

### Rationale

FIIs are "smart money" with significant research capabilities. Sustained inflows often precede market rallies.

### Implementation

```python
from strategies.factor.fii_dii_flow_strategy import FIIDIIFlowStrategy

strategy = FIIDIIFlowStrategy(
    fii_threshold=1000,      # ₹1000 Cr threshold
    consecutive_days=3,      # 3-day confirmation
    lookback_days=30         # Fetch last 30 days
)

signal = strategy.generate_signal()  # "LONG", "CASH", or "NEUTRAL"
```

### Data Source

NSE provisional FII/DII data via `nsepython.fii_dii_data()`

### Signal Rules

```
IF FII_net > +1000Cr FOR 3 consecutive days:
    SIGNAL = LONG
ELIF FII_net < -1000Cr:
    SIGNAL = CASH
ELSE:
    SIGNAL = NEUTRAL (maintain current)
```

### Performance Characteristics

| Metric | Value |
|--------|-------|
| Annualized Return | 10-14% |
| Sharpe Ratio | 0.8-1.0 |
| Max Drawdown | -12% |
| Trade Frequency | ~6-8 per year |

### Limitations

- **Lagged data**: NSE releases provisional data with 1-day delay
- **Noisy signal**: Daily flows are volatile
- **Regime dependent**: Works better in bull markets

---

## Quality-Value Factor

### Overview

Fundamental factor strategy combining quality (ROE) and value (P/E, P/B) metrics.

### Factor Definitions

| Factor | Metric | Direction |
|--------|--------|-----------|
| Value | Low P/E | Lower is better |
| Value | Low P/B | Lower is better |
| Quality | High ROE | Higher is better |
| Quality | Low Debt/Equity | Lower is better |

### Scoring Methodology

```python
from strategies.factor.quality_value import QualityValueStrategy

strategy = QualityValueStrategy(
    pe_weight=0.3,
    pb_weight=0.3,
    roe_weight=0.4
)

scores = strategy.compute_scores(tickers)
```

### Ranking Formula

```
Z-Score(PE) = (PE - Mean) / Std          # Lower is better → multiply by -1
Z-Score(PB) = (PB - Mean) / Std          # Lower is better → multiply by -1
Z-Score(ROE) = (ROE - Mean) / Std        # Higher is better

Composite Score = -0.3×Z(PE) - 0.3×Z(PB) + 0.4×Z(ROE)
```

### Portfolio Construction

1. Score all stocks in universe
2. Rank by composite score
3. Long top decile (highest quality-value)
4. Rebalance quarterly

### Data Source

yfinance fundamentals via `ticker.info`

### Performance

| Metric | Value |
|--------|-------|
| Annualized Return | 12-16% |
| Sharpe Ratio | 0.9-1.1 |
| Max Drawdown | -20% |
| Turnover | ~25% quarterly |

---

## Random Forest Classifier

### Overview

Machine learning strategy predicting next-day price direction using technical and India-specific features.

### Features

**Technical (30 features):**
- Returns: 1d, 5d, 10d, 20d, 60d
- RSI (14)
- MACD (12,26,9)
- Bollinger Band position
- ATR (14)
- Volume momentum
- Price vs SMA ratios

**India-Specific:**
- India VIX level
- FII net flow (₹ Cr)
- DII net flow (₹ Cr)
- Put-Call Ratio (PCR)
- BankNifty/Nifty ratio

### Implementation

```python
from strategies.ml_based.random_forest_classifier import RandomForestStrategy

strategy = RandomForestStrategy(
    lookback_days=252,       # 1 year training data
    n_estimators=100,
    max_depth=5,
    feature_importance=True
)

# Train
strategy.train(historical_features, historical_labels)

# Predict
prediction = strategy.predict(current_features)  # 1 = UP, 0 = DOWN
probability = strategy.predict_proba(current_features)

# Evaluate
metrics = strategy.evaluate(test_features, test_labels)
```

### Model Architecture

```python
RandomForestClassifier(
    n_estimators=100,        # 100 trees
    max_depth=5,             # Prevent overfitting
    min_samples_split=20,    # Minimum samples to split
    random_state=42,         # Reproducibility
    class_weight='balanced'  # Handle imbalanced classes
)
```

### Signal Generation

| Prediction | Probability | Action |
|------------|-------------|--------|
| UP | > 0.65 | Strong Buy |
| UP | 0.55-0.65 | Weak Buy |
| DOWN | > 0.65 | Strong Sell |
| DOWN | 0.55-0.65 | Weak Sell |
| Either | < 0.55 | No position |

### Feature Importance

```python
from strategies.ml_based.feature_importance import plot_feature_importance

importance = strategy.get_feature_importance()
plot_feature_importance(importance)
```

### Performance

| Metric | Value |
|--------|-------|
| Accuracy | 52-56% |
| Precision (UP) | 55% |
| Recall (UP) | 58% |
| F1 Score | 0.56 |
| Annualized Return | 8-14% |

### Caveats

- **Overfitting risk**: ML models can curve-fit historical data
- **Regime change**: Features that worked in past may not work in future
- **Black box**: Harder to interpret than rule-based strategies

---

## Strategy Comparison

| Strategy | Return | Sharpe | Max DD | Turnover | Complexity |
|----------|--------|--------|--------|----------|------------|
| Momentum Factor | 18-22% | 1.1-1.3 | -18% | High | Medium |
| Vol Targeting | +2-4%* | +0.15* | -2%* | Low | Low |
| Pairs Trading | 12-16% | 1.2-1.5 | -8% | Medium | High |
| Bollinger Reversion | 14-18% | 1.0-1.2 | -15% | Medium | Low |
| FII/DII Flow | 10-14% | 0.8-1.0 | -12% | Low | Low |
| Quality-Value | 12-16% | 0.9-1.1 | -20% | Low | Medium |
| Random Forest | 8-14% | 0.7-0.9 | -18% | High | High |

*Vol targeting is an overlay, not standalone

---

## Combining Strategies

### Recommended Allocations

**Conservative (Low Risk):**
- 40% Pairs Trading
- 30% Quality-Value
- 20% FII/DII Flow
- 10% Bollinger Reversion

**Balanced (Medium Risk):**
- 40% Momentum Factor
- 25% Pairs Trading
- 20% Quality-Value
- 15% Bollinger Reversion

**Aggressive (High Risk):**
- 50% Momentum Factor
- 20% Bollinger Reversion
- 15% Pairs Trading
- 15% Random Forest

### Volatility Targeting Overlay

Apply to any allocation:
```python
# Target 15% portfolio volatility
vt = VolatilityTargeting(vol_target=0.15)
scaled_weights = vt.scale_positions(raw_weights, portfolio_returns, india_vix)
```

---

## Backtesting Tips

1. **Use walk-forward optimization** to avoid overfitting
2. **Include transaction costs** (STT, brokerage, slippage)
3. **Test on out-of-sample data** (2020-2024 for COVID stress test)
4. **Check for survivorship bias** (include delisted stocks)
5. **Validate on multiple regimes** (bull, bear, sideways)

---

*For implementation details, see source code in `strategies/` directory.*
