"""Shared helpers for date windows and inflation-adjusted growth factors."""

from __future__ import annotations

from .tax_data import BASE_TAX_YEAR


def parse_ym(value: str) -> tuple[int, int]:
    year, month = value.split("-")
    return int(year), int(month)


def date_index(value: str, plan_start: str, plan_end: str) -> int:
    if value == "start":
        value = plan_start
    elif value == "end":
        value = plan_end
    year, month = parse_ym(value)
    return year * 12 + month


def is_active(start_date: str, end_date: str, current_index: int, plan_start: str, plan_end: str) -> bool:
    start_idx = date_index(start_date, plan_start, plan_end)
    end_idx = date_index(end_date, plan_start, plan_end)
    return start_idx <= current_index <= end_idx


def change_multiplier(
    *,
    change_over_time: str,
    change_rate: float | None,
    inflation_rate: float,
    years_elapsed: int,
) -> float:
    if years_elapsed <= 0:
        return 1.0
    if change_over_time == "fixed":
        annual_rate = 0.0
    elif change_over_time == "increase":
        annual_rate = change_rate or 0.0
    elif change_over_time == "decrease":
        annual_rate = -(change_rate or 0.0)
    elif change_over_time == "match_inflation":
        annual_rate = inflation_rate
    elif change_over_time == "inflation_plus":
        annual_rate = inflation_rate + (change_rate or 0.0)
    elif change_over_time == "inflation_minus":
        annual_rate = inflation_rate - (change_rate or 0.0)
    else:
        annual_rate = 0.0
    return (1.0 + annual_rate) ** years_elapsed


def year_factor(
    year: int,
    inflation_rate: float,
    *,
    base_year: int = BASE_TAX_YEAR,
    clamp_at_base_year: bool = False,
) -> float:
    delta = year - base_year
    if clamp_at_base_year:
        delta = max(0, delta)
    return (1.0 + inflation_rate) ** delta
