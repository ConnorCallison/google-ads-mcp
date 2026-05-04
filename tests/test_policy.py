from __future__ import annotations

import pytest

from google_ads_mcp.policy import validate_budget_change, validate_limit


def test_budget_change_allows_within_limit():
    validate_budget_change(
        current_amount_micros=1_000_000,
        new_amount_micros=1_200_000,
        max_change_pct=30,
    )


def test_budget_change_rejects_large_delta():
    with pytest.raises(ValueError, match="above GOOGLE_ADS_MAX_BUDGET_CHANGE_PCT"):
        validate_budget_change(
            current_amount_micros=1_000_000,
            new_amount_micros=1_500_000,
            max_change_pct=30,
        )


def test_validate_limit_caps_large_requests():
    assert validate_limit(10_000) == 1000
