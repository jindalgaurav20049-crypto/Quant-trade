"""FundLens domain package for mutual fund evaluation."""

from .modes import Mode, EntitlementService
from .models import (
    SchemeMaster,
    FundAnalyticsSnapshot,
    EvaluationContext,
    FundHealthScore,
    CalculationMetadata,
)
from .engine import evaluate_fund, build_health_score

__all__ = [
    "Mode",
    "EntitlementService",
    "SchemeMaster",
    "FundAnalyticsSnapshot",
    "EvaluationContext",
    "FundHealthScore",
    "CalculationMetadata",
    "evaluate_fund",
    "build_health_score",
]
