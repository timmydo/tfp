"""Roth conversion helpers."""

from __future__ import annotations

from .schema import RothConversion
from .tax_data import BASE_TAX_YEAR, FEDERAL_BRACKETS


def _year_factor(year: int, inflation_rate: float) -> float:
    delta = max(0, year - BASE_TAX_YEAR)
    return (1.0 + inflation_rate) ** delta


def _parse_bracket_rate(fill_to_bracket: str | None) -> float | None:
    if not fill_to_bracket:
        return None
    raw = fill_to_bracket.strip().replace("%", "")
    if not raw:
        return None
    try:
        return float(raw) / 100.0
    except ValueError:
        return None


def _bracket_upper_bound(filing_status: str, year: int, inflation_rate: float, marginal_rate: float) -> float | None:
    status = filing_status if filing_status in FEDERAL_BRACKETS[BASE_TAX_YEAR] else "single"
    factor = _year_factor(year, inflation_rate)
    for upper, rate in FEDERAL_BRACKETS[BASE_TAX_YEAR][status]:
        if abs(rate - marginal_rate) < 1e-9:
            return None if upper is None else upper * factor
    return None


def _date_index(value: str, plan_start: str, plan_end: str) -> int:
    if value == "start":
        value = plan_start
    elif value == "end":
        value = plan_end
    year, month = value.split("-")
    return int(year) * 12 + int(month)


def _active(conversion: RothConversion, current_index: int, plan_start: str, plan_end: str) -> bool:
    start = _date_index(conversion.start_date, plan_start, plan_end)
    end = _date_index(conversion.end_date, plan_start, plan_end)
    return start <= current_index <= end


def execute_roth_conversions(
    *,
    conversions: list[RothConversion],
    balances: dict[str, float],
    current_year: int,
    current_month: int,
    current_index: int,
    plan_start: str,
    plan_end: str,
    filing_status: str,
    inflation_rate: float,
    ytd_taxable_ordinary_income: float,
) -> tuple[float, float]:
    """Execute applicable Roth conversions for month.

    Returns (total_converted, ordinary_income_added).
    """
    total_converted = 0.0
    ordinary_income_added = 0.0
    projected_ordinary_income = max(0.0, ytd_taxable_ordinary_income)

    for conversion in conversions:
        if not _active(conversion, current_index, plan_start, plan_end):
            continue

        source_balance = max(0.0, balances.get(conversion.from_account, 0.0))
        if source_balance <= 0:
            continue

        amount = 0.0
        if conversion.fill_to_bracket:
            # Fill-to-bracket executes as a December lump sum.
            if current_month != 12:
                continue
            rate = _parse_bracket_rate(conversion.fill_to_bracket)
            if rate is None:
                continue
            upper = _bracket_upper_bound(filing_status, current_year, inflation_rate, rate)
            if upper is None:
                continue
            room = max(0.0, upper - projected_ordinary_income)
            amount = min(source_balance, room)
        elif conversion.annual_amount is not None:
            amount = min(source_balance, max(0.0, conversion.annual_amount / 12.0))

        if amount <= 0:
            continue

        balances[conversion.from_account] -= amount
        balances[conversion.to_account] += amount
        total_converted += amount
        ordinary_income_added += amount
        projected_ordinary_income += amount

    return total_converted, ordinary_income_added
