"""Data contracts and evaluation models for FundLens."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass(frozen=True)
class SchemeMaster:
    """Canonical scheme identity and classification."""

    scheme_code: str
    scheme_name: str
    amc_name: str
    sebi_category: str
    benchmark_name: str
    inception_date: datetime
    expense_ratio: float
    fund_manager_name: str
    merger_history: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class CalculationMetadata:
    """Calculation governance metadata for auditability."""

    calculation_version: str
    calculated_at: datetime
    data_start_date: datetime
    data_end_date: datetime
    insufficient_data_flags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class FundHealthScore:
    """Composite score with transparent decomposition."""

    total_score: float
    return_score: float
    risk_score: float
    consistency_score: float
    cost_score: float
    notes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class FundAnalyticsSnapshot:
    """Read-optimized snapshot for a scheme at a point in time."""

    scheme_code: str
    nav_date: datetime
    returns: Dict[str, float]
    risk: Dict[str, float]
    risk_adjusted: Dict[str, float]
    health_score: FundHealthScore
    metadata: CalculationMetadata


@dataclass(frozen=True)
class EvaluationContext:
    """Context required for category-aware metric presentation."""

    asset_type: str  # e.g. equity, hybrid, debt
    risk_free_rate: float = 0.06
    benchmark_returns: Optional[List[float]] = None
    category_avg_returns: Optional[List[float]] = None
