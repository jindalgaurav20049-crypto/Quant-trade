"""Evaluation engine for FundLens return/risk/risk-adjusted metrics."""

from __future__ import annotations

import math
from statistics import mean
from typing import Dict, Iterable, List, Sequence

from .models import EvaluationContext, FundHealthScore


def _safe_mean(values: Sequence[float]) -> float:
    filtered = [v for v in values if v is not None]
    return sum(filtered) / len(filtered) if filtered else 0.0


def _std_dev(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = _safe_mean(values)
    variance = sum((v - mu) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(max(variance, 0.0))


def _compound(values: Iterable[float]) -> float:
    result = 1.0
    for value in values:
        result *= 1.0 + value
    return result


def absolute_return(period_returns: Sequence[float]) -> float:
    return _compound(period_returns) - 1.0


def cagr(period_returns: Sequence[float], years: float) -> float:
    if years <= 0:
        return 0.0
    gross = _compound(period_returns)
    if gross <= 0:
        return -1.0
    return gross ** (1.0 / years) - 1.0


def rolling_returns(period_returns: Sequence[float], window: int) -> List[float]:
    if window <= 0 or len(period_returns) < window:
        return []
    return [
        absolute_return(period_returns[i : i + window])
        for i in range(0, len(period_returns) - window + 1)
    ]


def percentile_rank(value: float, peer_values: Sequence[float]) -> float:
    if not peer_values:
        return 0.0
    below_or_equal = sum(1 for peer in peer_values if peer <= value)
    return 100.0 * below_or_equal / len(peer_values)


def beta(fund_returns: Sequence[float], benchmark_returns: Sequence[float]) -> float:
    n = min(len(fund_returns), len(benchmark_returns))
    if n < 2:
        return 0.0
    f = list(fund_returns[:n])
    b = list(benchmark_returns[:n])
    mf = _safe_mean(f)
    mb = _safe_mean(b)
    cov = sum((f[i] - mf) * (b[i] - mb) for i in range(n)) / (n - 1)
    var_b = sum((x - mb) ** 2 for x in b) / (n - 1)
    return cov / var_b if var_b else 0.0


def downside_deviation(fund_returns: Sequence[float], mar: float = 0.0) -> float:
    downside = [min(0.0, r - mar) for r in fund_returns]
    return _std_dev(downside)


def max_drawdown(fund_returns: Sequence[float]) -> float:
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in fund_returns:
        equity *= 1.0 + r
        peak = max(peak, equity)
        dd = (equity - peak) / peak
        max_dd = min(max_dd, dd)
    return max_dd


def var_95(fund_returns: Sequence[float]) -> float:
    if not fund_returns:
        return 0.0
    ordered = sorted(fund_returns)
    idx = max(0, int(math.floor(0.05 * (len(ordered) - 1))))
    return ordered[idx]


def upside_capture_ratio(
    fund_returns: Sequence[float], benchmark_returns: Sequence[float]
) -> float:
    pairs = [(f, b) for f, b in zip(fund_returns, benchmark_returns) if b > 0]
    if not pairs:
        return 0.0
    fund_up = _safe_mean([f for f, _ in pairs])
    bench_up = _safe_mean([b for _, b in pairs])
    return (fund_up / bench_up) * 100.0 if bench_up else 0.0


def downside_capture_ratio(
    fund_returns: Sequence[float], benchmark_returns: Sequence[float]
) -> float:
    pairs = [(f, b) for f, b in zip(fund_returns, benchmark_returns) if b < 0]
    if not pairs:
        return 0.0
    fund_down = _safe_mean([f for f, _ in pairs])
    bench_down = _safe_mean([b for _, b in pairs])
    return (fund_down / bench_down) * 100.0 if bench_down else 0.0


def sharpe_ratio(fund_returns: Sequence[float], risk_free_rate: float = 0.06) -> float:
    if not fund_returns:
        return 0.0
    monthly_rf = (1.0 + risk_free_rate) ** (1.0 / 12.0) - 1.0
    excess = [r - monthly_rf for r in fund_returns]
    sigma = _std_dev(fund_returns)
    return (_safe_mean(excess) / sigma) * math.sqrt(12.0) if sigma else 0.0


def sortino_ratio(fund_returns: Sequence[float], risk_free_rate: float = 0.06) -> float:
    if not fund_returns:
        return 0.0
    monthly_rf = (1.0 + risk_free_rate) ** (1.0 / 12.0) - 1.0
    excess = [r - monthly_rf for r in fund_returns]
    down_dev = downside_deviation(fund_returns, mar=monthly_rf)
    return (_safe_mean(excess) / down_dev) * math.sqrt(12.0) if down_dev else 0.0


def treynor_ratio(
    fund_returns: Sequence[float], benchmark_returns: Sequence[float], risk_free_rate: float = 0.06
) -> float:
    if not fund_returns or not benchmark_returns:
        return 0.0
    monthly_rf = (1.0 + risk_free_rate) ** (1.0 / 12.0) - 1.0
    fund_beta = beta(fund_returns, benchmark_returns)
    return (_safe_mean(fund_returns) - monthly_rf) / fund_beta if fund_beta else 0.0


def jensens_alpha(
    fund_returns: Sequence[float], benchmark_returns: Sequence[float], risk_free_rate: float = 0.06
) -> float:
    if not fund_returns or not benchmark_returns:
        return 0.0
    monthly_rf = (1.0 + risk_free_rate) ** (1.0 / 12.0) - 1.0
    b = beta(fund_returns, benchmark_returns)
    expected = monthly_rf + b * (_safe_mean(benchmark_returns) - monthly_rf)
    return _safe_mean(fund_returns) - expected


def _clamp_0_100(value: float) -> float:
    return max(0.0, min(100.0, value))


def build_health_score(
    trailing_return: float,
    max_dd: float,
    consistency: float,
    expense_ratio: float,
) -> FundHealthScore:
    """Build transparent composite score from decomposable sub-scores."""
    return_score = _clamp_0_100((trailing_return + 0.20) * 250.0)
    risk_score = _clamp_0_100(100.0 + max_dd * 500.0)
    consistency_score = _clamp_0_100(consistency)
    cost_score = _clamp_0_100(100.0 - expense_ratio * 50.0)

    total = (
        0.35 * return_score
        + 0.25 * risk_score
        + 0.25 * consistency_score
        + 0.15 * cost_score
    )

    notes = [
        "Total score is weighted: Return 35%, Risk 25%, Consistency 25%, Cost 15%.",
        "Scores are clipped to 0-100 for stability across categories.",
    ]

    return FundHealthScore(
        total_score=round(total, 2),
        return_score=round(return_score, 2),
        risk_score=round(risk_score, 2),
        consistency_score=round(consistency_score, 2),
        cost_score=round(cost_score, 2),
        notes=notes,
    )


def evaluate_fund(
    fund_returns: Sequence[float],
    context: EvaluationContext,
    expense_ratio: float,
    peer_trailing_returns: Sequence[float] | None = None,
) -> Dict[str, Dict[str, float | bool | str]]:
    """Evaluate fund metrics grouped by module with category-aware applicability."""
    bench = context.benchmark_returns or []
    category = context.category_avg_returns or []
    trailing = absolute_return(fund_returns)
    years = max(len(fund_returns) / 12.0, 1 / 12)
    rolling_12m = rolling_returns(fund_returns, 12)

    returns_module = {
        "absolute_return": trailing,
        "cagr": cagr(fund_returns, years),
        "rolling_return_mean_1y": _safe_mean(rolling_12m),
        "vs_benchmark": trailing - absolute_return(bench) if bench else 0.0,
        "vs_category_avg": trailing - absolute_return(category) if category else 0.0,
        "percentile_rank": percentile_rank(trailing, peer_trailing_returns or []),
    }

    risk_module = {
        "std_dev": _std_dev(fund_returns),
        "beta": beta(fund_returns, bench) if bench else 0.0,
        "downside_deviation": downside_deviation(fund_returns),
        "max_drawdown": max_drawdown(fund_returns),
        "var_95": var_95(fund_returns),
        "upside_capture_ratio": upside_capture_ratio(fund_returns, bench) if bench else 0.0,
        "downside_capture_ratio": downside_capture_ratio(fund_returns, bench) if bench else 0.0,
    }

    sharpe_applicable = context.asset_type.lower() != "debt"
    risk_adj_module = {
        "sharpe_ratio": sharpe_ratio(fund_returns, context.risk_free_rate) if sharpe_applicable else 0.0,
        "sharpe_applicable": sharpe_applicable,
        "sortino_ratio": sortino_ratio(fund_returns, context.risk_free_rate),
        "treynor_ratio": treynor_ratio(fund_returns, bench, context.risk_free_rate) if bench else 0.0,
        "jensens_alpha": jensens_alpha(fund_returns, bench, context.risk_free_rate) if bench else 0.0,
    }

    consistency = percentile_rank(_safe_mean(rolling_12m), rolling_12m) if rolling_12m else 0.0
    health_score = build_health_score(
        trailing_return=returns_module["cagr"],
        max_dd=risk_module["max_drawdown"],
        consistency=consistency,
        expense_ratio=expense_ratio,
    )

    return {
        "returns": returns_module,
        "risk": risk_module,
        "risk_adjusted": risk_adj_module,
        "health_score": {
            "total": health_score.total_score,
            "return_score": health_score.return_score,
            "risk_score": health_score.risk_score,
            "consistency_score": health_score.consistency_score,
            "cost_score": health_score.cost_score,
        },
    }
