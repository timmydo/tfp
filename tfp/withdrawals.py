"""Withdrawal strategy logic."""

from __future__ import annotations

from dataclasses import dataclass

from .cost_basis import CostBasisTracker
from .schema import Account, WithdrawalStrategy


@dataclass(slots=True)
class WithdrawalEvent:
    account: str
    amount: float
    realized_gain: float


def _ordered_account_names(accounts: dict[str, Account], strategy: WithdrawalStrategy) -> list[str]:
    if strategy.use_account_specific and strategy.account_specific_order:
        return [name for name in strategy.account_specific_order if name in accounts]

    names: list[str] = []
    if strategy.order:
        for account_type in strategy.order:
            for account in accounts.values():
                if account.type == account_type and account.name not in names:
                    names.append(account.name)

    for account in accounts.values():
        if account.name not in names:
            names.append(account.name)
    return names


PENALTY_AGE = 59.5
PENALTY_ACCOUNT_TYPES = {"401k", "traditional_ira", "roth_ira"}


def _is_penalty_eligible(account: Account, owner_ages: dict[str, float]) -> bool:
    """Return True if withdrawing from this account would incur an early withdrawal penalty."""
    return (
        account.type in PENALTY_ACCOUNT_TYPES
        and owner_ages.get(account.owner, 0.0) < PENALTY_AGE
    )


def _withdraw_from_accounts(
    *,
    shortfall: float,
    ordered_names: list[str],
    balances: dict[str, float],
    accounts: dict[str, Account],
    cash_account_name: str,
    cost_basis: dict[str, CostBasisTracker],
    events: list[WithdrawalEvent],
    skip_penalty: bool,
    owner_ages: dict[str, float],
) -> tuple[float, float]:
    """Withdraw from accounts in order. Returns (remaining_shortfall, realized_gains)."""
    realized_gains = 0.0
    for name in ordered_names:
        if shortfall <= 0:
            break
        if name == cash_account_name:
            continue

        account = accounts[name]
        if not account.allow_withdrawals:
            continue

        if skip_penalty and _is_penalty_eligible(account, owner_ages):
            continue

        available = max(0.0, balances.get(name, 0.0))
        if available <= 0:
            continue

        amount = min(available, shortfall)
        balance_before = balances[name]
        balances[name] -= amount
        balances[cash_account_name] += amount

        gain = 0.0
        if account.type == "taxable_brokerage" and name in cost_basis:
            gain = cost_basis[name].withdraw(amount, balance_before)
            realized_gains += gain

        events.append(WithdrawalEvent(account=name, amount=amount, realized_gain=gain))
        shortfall -= amount

    return shortfall, realized_gains


def cover_shortfall(
    *,
    shortfall: float,
    balances: dict[str, float],
    accounts: dict[str, Account],
    strategy: WithdrawalStrategy,
    cash_account_name: str,
    cost_basis: dict[str, CostBasisTracker],
    owner_ages: dict[str, float],
) -> tuple[float, list[WithdrawalEvent], float]:
    """Try to fund shortfall into cash account.

    Uses a two-pass approach: first withdraws from non-penalized accounts,
    then falls back to penalty-eligible accounts as a last resort.

    Returns remaining shortfall, withdrawal events, and total realized capital gains.
    """
    if shortfall <= 0:
        return 0.0, [], 0.0

    events: list[WithdrawalEvent] = []
    ordered_names = _ordered_account_names(accounts, strategy)

    # First pass: skip penalty-eligible accounts
    shortfall, gains1 = _withdraw_from_accounts(
        shortfall=shortfall,
        ordered_names=ordered_names,
        balances=balances,
        accounts=accounts,
        cash_account_name=cash_account_name,
        cost_basis=cost_basis,
        events=events,
        skip_penalty=True,
        owner_ages=owner_ages,
    )

    # Second pass: use penalty-eligible accounts as last resort
    if shortfall > 0:
        shortfall, gains2 = _withdraw_from_accounts(
            shortfall=shortfall,
            ordered_names=ordered_names,
            balances=balances,
            accounts=accounts,
            cash_account_name=cash_account_name,
            cost_basis=cost_basis,
            events=events,
            skip_penalty=False,
            owner_ages=owner_ages,
        )
    else:
        gains2 = 0.0

    return max(0.0, shortfall), events, gains1 + gains2
