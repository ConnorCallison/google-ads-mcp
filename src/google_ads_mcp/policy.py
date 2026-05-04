from __future__ import annotations


def validate_budget_change(
    *,
    current_amount_micros: int | None,
    new_amount_micros: int,
    max_change_pct: float,
) -> None:
    if new_amount_micros <= 0:
        raise ValueError("Budget amount must be greater than zero.")
    if current_amount_micros is None:
        return
    if current_amount_micros <= 0:
        raise ValueError("Current budget amount is zero or missing; refusing percent-based change.")
    change_pct = abs(new_amount_micros - current_amount_micros) / current_amount_micros * 100
    if change_pct > max_change_pct:
        rounded = round(change_pct, 2)
        raise ValueError(
            f"Budget change is {rounded}%, above "
            f"GOOGLE_ADS_MAX_BUDGET_CHANGE_PCT={max_change_pct}%."
        )


def validate_limit(value: int, *, max_value: int = 1000) -> int:
    if value < 1:
        raise ValueError("limit must be at least 1")
    return min(value, max_value)
