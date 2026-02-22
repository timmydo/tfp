"""Real asset modeling helpers."""

from __future__ import annotations

from dataclasses import dataclass

from .schema import RealAsset


@dataclass(slots=True)
class RealAssetState:
    asset: RealAsset
    current_value: float
    mortgage_balance: float


def annual_to_monthly_rate(annual_rate: float) -> float:
    if annual_rate <= -1.0:
        return -1.0
    return (1.0 + annual_rate) ** (1.0 / 12.0) - 1.0


def change_rate_for_year(change_over_time: str, change_rate: float | None, inflation_rate: float) -> float:
    if change_over_time == "fixed":
        return 0.0
    if change_over_time == "increase":
        return change_rate or 0.0
    if change_over_time == "match_inflation":
        return inflation_rate
    if change_over_time == "inflation_plus":
        return inflation_rate + (change_rate or 0.0)
    if change_over_time == "inflation_minus":
        return inflation_rate - (change_rate or 0.0)
    return 0.0


def appreciate_asset(state: RealAssetState, annual_rate: float) -> float:
    monthly_rate = annual_to_monthly_rate(annual_rate)
    growth = state.current_value * monthly_rate
    state.current_value += growth
    return growth


def mortgage_payment(state: RealAssetState) -> tuple[float, float, float]:
    """Return (total_payment, principal_paid, interest_paid)."""
    mortgage = state.asset.mortgage
    if mortgage is None or state.mortgage_balance <= 0:
        return 0.0, 0.0, 0.0

    monthly_interest = mortgage.interest_rate / 12.0
    interest_component = state.mortgage_balance * monthly_interest
    principal_component = max(0.0, mortgage.payment - interest_component)
    principal_component = min(principal_component, state.mortgage_balance)
    total_payment = interest_component + principal_component
    state.mortgage_balance -= principal_component
    return total_payment, principal_component, interest_component


def property_tax_monthly(state: RealAssetState) -> float:
    return max(0.0, state.current_value * state.asset.property_tax_rate / 12.0)
