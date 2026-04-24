"""Mode and entitlement logic for FundLens."""

from dataclasses import dataclass
from enum import Enum


class Mode(str, Enum):
    """Supported FundLens experience modes."""

    BEGINNER = "beginner"
    ADVANCED = "advanced"


PREMIUM_FEATURES = {
    "multi_factor_scoring",
    "fund_manager_analytics",
    "rolling_return_heatmap",
    "custom_screener",
    "portfolio_overlap",
    "export_pdf_excel",
}


@dataclass(frozen=True)
class EntitlementService:
    """Simple freemium entitlement checks."""

    has_premium: bool = False

    def can_use_mode(self, mode: Mode) -> bool:
        """Advanced mode requires premium entitlement."""
        return mode == Mode.BEGINNER or self.has_premium

    def can_use_feature(self, feature_key: str, mode: Mode) -> bool:
        """Checks mode + feature availability under freemium model."""
        if not self.can_use_mode(mode):
            return False
        if feature_key in PREMIUM_FEATURES and not self.has_premium:
            return False
        return True

    def max_compare_funds(self, mode: Mode) -> int:
        """Beginner mode restricts comparison to two funds."""
        return 2 if mode == Mode.BEGINNER else 8
