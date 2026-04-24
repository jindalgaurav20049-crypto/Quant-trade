"""Screener utilities for FundLens analytics snapshots."""

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class ScreenerRule:
    """Single numeric screen rule."""

    metric_key: str
    min_value: float | None = None
    max_value: float | None = None



def apply_screener(
    rows: Iterable[Dict[str, float]],
    rules: List[ScreenerRule],
) -> List[Dict[str, float]]:
    """Filter rows that satisfy all screener rules."""
    output: List[Dict[str, float]] = []
    for row in rows:
        is_match = True
        for rule in rules:
            if rule.metric_key not in row:
                is_match = False
                break
            value = row[rule.metric_key]
            if rule.min_value is not None and value < rule.min_value:
                is_match = False
                break
            if rule.max_value is not None and value > rule.max_value:
                is_match = False
                break
        if is_match:
            output.append(row)
    return output
