"""Required Minimum Distribution helpers."""

from __future__ import annotations

from .schema import Account, RMDSettings

# IRS Uniform Lifetime Table (selected ages, v1 simplification support).
UNIFORM_LIFETIME_DIVISORS: dict[int, float] = {
    73: 26.5,
    74: 25.5,
    75: 24.6,
    76: 23.7,
    77: 22.9,
    78: 22.0,
    79: 21.1,
    80: 20.2,
    81: 19.4,
    82: 18.5,
    83: 17.7,
    84: 16.8,
    85: 16.0,
    86: 15.2,
    87: 14.4,
    88: 13.7,
    89: 12.9,
    90: 12.2,
    91: 11.5,
    92: 10.8,
    93: 10.1,
    94: 9.5,
    95: 8.9,
    96: 8.4,
    97: 7.8,
    98: 7.3,
    99: 6.8,
    100: 6.4,
    101: 6.0,
    102: 5.6,
    103: 5.2,
    104: 4.9,
    105: 4.6,
    106: 4.3,
    107: 4.1,
    108: 3.9,
    109: 3.7,
    110: 3.5,
    111: 3.4,
    112: 3.3,
    113: 3.1,
    114: 3.0,
    115: 2.9,
    116: 2.8,
    117: 2.7,
    118: 2.5,
    119: 2.3,
    120: 2.0,
}


def _age_whole_years(age_years: float) -> int:
    return int(max(0.0, age_years))


def divisor_for_age(age_years: float) -> float | None:
    age = _age_whole_years(age_years)
    if age < min(UNIFORM_LIFETIME_DIVISORS):
        return None
    if age in UNIFORM_LIFETIME_DIVISORS:
        return UNIFORM_LIFETIME_DIVISORS[age]
    if age > max(UNIFORM_LIFETIME_DIVISORS):
        return UNIFORM_LIFETIME_DIVISORS[max(UNIFORM_LIFETIME_DIVISORS)]
    return None


def compute_rmd_amount(prior_year_end_balance: float, age_years: float) -> float:
    divisor = divisor_for_age(age_years)
    if divisor is None or prior_year_end_balance <= 0:
        return 0.0
    return max(0.0, prior_year_end_balance / divisor)


def execute_rmds(
    *,
    settings: RMDSettings,
    accounts_by_name: dict[str, Account],
    balances: dict[str, float],
    prior_year_end_balances: dict[str, float],
    owner_ages: dict[str, float],
) -> tuple[float, float]:
    """Execute December RMDs and deposit proceeds to destination account.

    Returns (total_withdrawals, ordinary_income_added).
    """
    if not settings.enabled:
        return 0.0, 0.0

    total_withdrawn = 0.0
    for account_name in settings.accounts:
        account = accounts_by_name.get(account_name)
        if account is None:
            continue

        owner_age = owner_ages.get(account.owner, 0.0)
        if owner_age < float(settings.rmd_start_age):
            continue

        prior_balance = max(0.0, prior_year_end_balances.get(account_name, balances.get(account_name, 0.0)))
        target = compute_rmd_amount(prior_balance, owner_age)
        if target <= 0:
            continue

        available = max(0.0, balances.get(account_name, 0.0))
        amount = min(available, target)
        if amount <= 0:
            continue

        balances[account_name] -= amount
        balances[settings.destination_account] += amount
        total_withdrawn += amount

    return total_withdrawn, total_withdrawn
