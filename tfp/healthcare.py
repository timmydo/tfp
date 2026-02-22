"""Healthcare monthly costs and IRMAA surcharge modeling."""

from __future__ import annotations

from .schema import Healthcare, HealthcarePostMedicare
from .tax_data import BASE_TAX_YEAR, IRMAA_BRACKETS


def _year_factor(year: int, inflation_rate: float) -> float:
    delta = max(0, year - BASE_TAX_YEAR)
    return (1.0 + inflation_rate) ** delta


def _date_index(value: str, plan_start: str, plan_end: str) -> int:
    if value == "start":
        value = plan_start
    elif value == "end":
        value = plan_end
    year, month = value.split("-")
    return int(year) * 12 + int(month)


def _is_active(start_date: str, end_date: str, current_index: int, plan_start: str, plan_end: str) -> bool:
    return _date_index(start_date, plan_start, plan_end) <= current_index <= _date_index(end_date, plan_start, plan_end)


def _change_multiplier(change_over_time: str, change_rate: float | None, inflation_rate: float, years_elapsed: int) -> float:
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


def _irmaa_surcharge_monthly(
    *,
    filing_status: str,
    year: int,
    inflation_rate: float,
    lookback_magi: float,
) -> tuple[float, float]:
    status = filing_status if filing_status in IRMAA_BRACKETS[BASE_TAX_YEAR] else "single"
    factor = _year_factor(year, inflation_rate)

    for upper, (part_b, part_d) in IRMAA_BRACKETS[BASE_TAX_YEAR][status]:
        upper_adj = None if upper is None else upper * factor
        if upper_adj is None or lookback_magi <= upper_adj:
            return part_b * factor, part_d * factor

    return 0.0, 0.0


def _post_medicare_active(item: HealthcarePostMedicare, owner_age: float, current_index: int, plan_start: str, plan_end: str) -> bool:
    if owner_age < 65.0:
        return False
    start = item.medicare_start_date or "start"
    return _is_active(start, "end", current_index, plan_start, plan_end)


def compute_monthly_healthcare_cost(
    *,
    healthcare: Healthcare,
    owner_ages: dict[str, float],
    current_year: int,
    current_index: int,
    plan_start: str,
    plan_end: str,
    inflation_rate: float,
    filing_status: str,
    irmaa_magi_history: dict[int, float],
) -> tuple[float, float]:
    """Return (healthcare_cost, irmaa_surcharge_component) for current month."""
    start_year = int(plan_start.split("-")[0])
    years_elapsed = max(0, current_year - start_year)

    total = 0.0
    irmaa_component = 0.0

    for item in healthcare.pre_medicare:
        start = item.start_date or "start"
        end = item.end_date or "end"
        if not _is_active(start, end, current_index, plan_start, plan_end):
            continue
        if owner_ages.get(item.owner, 0.0) >= 65.0:
            continue
        factor = _change_multiplier(item.change_over_time, item.change_rate, inflation_rate, years_elapsed)
        total += (item.monthly_premium + item.annual_out_of_pocket / 12.0) * factor

    for item in healthcare.post_medicare:
        owner_age = owner_ages.get(item.owner, 0.0)
        if not _post_medicare_active(item, owner_age, current_index, plan_start, plan_end):
            continue

        factor = _change_multiplier(item.change_over_time, item.change_rate, inflation_rate, years_elapsed)
        monthly = (
            item.part_b_monthly_premium
            + item.supplement_monthly_premium
            + item.part_d_monthly_premium
            + item.annual_out_of_pocket / 12.0
        ) * factor
        total += monthly

        if healthcare.irmaa.enabled:
            lookback_year = current_year - healthcare.irmaa.lookback_years
            lookback_magi = max(0.0, irmaa_magi_history.get(lookback_year, 0.0))
            part_b_surcharge, part_d_surcharge = _irmaa_surcharge_monthly(
                filing_status=filing_status,
                year=current_year,
                inflation_rate=inflation_rate,
                lookback_magi=lookback_magi,
            )
            surcharge = part_b_surcharge + part_d_surcharge
            irmaa_component += surcharge
            total += surcharge

    return total, irmaa_component
