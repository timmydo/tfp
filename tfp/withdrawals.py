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


def cover_shortfall(
    *,
    shortfall: float,
    balances: dict[str, float],
    accounts: dict[str, Account],
    strategy: WithdrawalStrategy,
    cash_account_name: str,
    cost_basis: dict[str, CostBasisTracker],
) -> tuple[float, list[WithdrawalEvent], float]:
    """Try to fund shortfall into cash account.

    Returns remaining shortfall, withdrawal events, and total realized capital gains.
    """
    if shortfall <= 0:
        return 0.0, [], 0.0

    events: list[WithdrawalEvent] = []
    realized_gains = 0.0

    for name in _ordered_account_names(accounts, strategy):
        if shortfall <= 0:
            break
        if name == cash_account_name:
            continue

        account = accounts[name]
        if not account.allow_withdrawals:
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

    return max(0.0, shortfall), events, realized_gains
