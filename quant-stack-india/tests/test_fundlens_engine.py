"""Tests for FundLens evaluation engine and mode gating."""

import unittest

from fundlens.engine import (
    absolute_return,
    rolling_returns,
    evaluate_fund,
    build_health_score,
)
from fundlens.modes import EntitlementService, Mode
from fundlens.models import EvaluationContext


class TestFundLensEngine(unittest.TestCase):
    def test_absolute_and_rolling_returns(self):
        monthly = [0.01] * 12
        self.assertGreater(absolute_return(monthly), 0.12)
        self.assertEqual(len(rolling_returns(monthly * 2, 12)), 13)

    def test_evaluate_fund_modules_present(self):
        fund = [0.01, 0.005, -0.01, 0.012, 0.004, -0.002] * 12
        bench = [0.008, 0.004, -0.012, 0.01, 0.003, -0.003] * 12
        context = EvaluationContext(
            asset_type="equity",
            risk_free_rate=0.06,
            benchmark_returns=bench,
            category_avg_returns=bench,
        )

        result = evaluate_fund(
            fund_returns=fund,
            context=context,
            expense_ratio=1.2,
            peer_trailing_returns=[0.08, 0.10, 0.12],
        )

        self.assertIn("returns", result)
        self.assertIn("risk", result)
        self.assertIn("risk_adjusted", result)
        self.assertIn("health_score", result)

    def test_debt_sharpe_applicability_flag(self):
        returns = [0.004, 0.003, 0.005, -0.001] * 12
        context = EvaluationContext(asset_type="debt", benchmark_returns=returns)
        result = evaluate_fund(returns, context, expense_ratio=0.6)
        self.assertFalse(result["risk_adjusted"]["sharpe_applicable"])

    def test_health_score_decomposition(self):
        score = build_health_score(
            trailing_return=0.15,
            max_dd=-0.08,
            consistency=70,
            expense_ratio=1.0,
        )
        self.assertGreaterEqual(score.total_score, 0)
        self.assertLessEqual(score.total_score, 100)
        self.assertEqual(len(score.notes), 2)


class TestEntitlements(unittest.TestCase):
    def test_beginner_free_advanced_paid(self):
        free = EntitlementService(has_premium=False)
        paid = EntitlementService(has_premium=True)

        self.assertTrue(free.can_use_mode(Mode.BEGINNER))
        self.assertFalse(free.can_use_mode(Mode.ADVANCED))
        self.assertTrue(paid.can_use_mode(Mode.ADVANCED))
        self.assertEqual(free.max_compare_funds(Mode.BEGINNER), 2)


if __name__ == "__main__":
    unittest.main()
