"""Social Security monthly benefit modeling."""

from __future__ import annotations

from .schema import SocialSecurity


def _age_months(age_years: float) -> int:
    return int(max(0.0, age_years * 12.0))


def _claim_months(item: SocialSecurity) -> int:
    return item.claiming_age_years * 12 + item.claiming_age_months


def _fra_months(item: SocialSecurity) -> int:
    return item.fra_age_years * 12 + item.fra_age_months


def _cola_rate(item: SocialSecurity, inflation_rate: float) -> float:
    if item.cola_assumption == "fixed":
        return item.cola_rate or 0.0
    if item.cola_assumption == "match_inflation":
        return inflation_rate
    if item.cola_assumption == "inflation_plus":
        return inflation_rate + (item.cola_rate or 0.0)
    if item.cola_assumption == "inflation_minus":
        return inflation_rate - (item.cola_rate or 0.0)
    return 0.0


def _claiming_adjustment(item: SocialSecurity) -> float:
    diff = _claim_months(item) - _fra_months(item)
    if diff == 0:
        return 1.0
    if diff < 0:
        early = abs(diff)
        first_36 = min(36, early)
        additional = max(0, early - 36)
        reduction = first_36 * (5.0 / 900.0) + additional * (5.0 / 1200.0)
        return max(0.0, 1.0 - reduction)
    delayed_credit = diff * (2.0 / 300.0)
    return 1.0 + delayed_credit


def _base_monthly_benefit(item: SocialSecurity) -> float:
    return max(0.0, item.pia_at_fra * _claiming_adjustment(item))


def _owner_monthly_benefit(item: SocialSecurity, age_years: float, inflation_rate: float) -> float:
    age_m = _age_months(age_years)
    claim_m = _claim_months(item)
    if age_m < claim_m:
        return 0.0

    years_after_claim = max(0, (age_m - claim_m) // 12)
    cola = _cola_rate(item, inflation_rate)
    return _base_monthly_benefit(item) * ((1.0 + cola) ** years_after_claim)


def _spousal_monthly_benefit(owner: SocialSecurity, spouse: SocialSecurity, age_years: float, inflation_rate: float) -> float:
    age_m = _age_months(age_years)
    if age_m < _claim_months(owner):
        return 0.0

    base = 0.5 * max(0.0, spouse.pia_at_fra) * _claiming_adjustment(owner)
    years_after_claim = max(0, (age_m - _claim_months(owner)) // 12)
    cola = _cola_rate(owner, inflation_rate)
    return max(0.0, base * ((1.0 + cola) ** years_after_claim))


def monthly_social_security_income(
    *,
    entries: list[SocialSecurity],
    owner_ages: dict[str, float],
    inflation_rate: float,
) -> tuple[float, dict[str, float]]:
    """Return (total_monthly_income, by_owner_monthly_income)."""
    by_owner = {item.owner: item for item in entries}
    owner_benefits: dict[str, float] = {}

    for owner, item in by_owner.items():
        owner_benefits[owner] = _owner_monthly_benefit(item, owner_ages.get(owner, 0.0), inflation_rate)

    if "primary" in by_owner and "spouse" in by_owner:
        primary = by_owner["primary"]
        spouse = by_owner["spouse"]

        if primary.pia_at_fra < 0.5 * spouse.pia_at_fra:
            owner_benefits["primary"] = max(
                owner_benefits.get("primary", 0.0),
                _spousal_monthly_benefit(primary, spouse, owner_ages.get("primary", 0.0), inflation_rate),
            )

        if spouse.pia_at_fra < 0.5 * primary.pia_at_fra:
            owner_benefits["spouse"] = max(
                owner_benefits.get("spouse", 0.0),
                _spousal_monthly_benefit(spouse, primary, owner_ages.get("spouse", 0.0), inflation_rate),
            )

    total = sum(max(0.0, value) for value in owner_benefits.values())
    return total, owner_benefits
