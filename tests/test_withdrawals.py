"""Tests for withdrawal strategy penalty-aware logic."""

from tfp.cost_basis import CostBasisTracker
from tfp.schema import Account, WithdrawalStrategy
from tfp.withdrawals import cover_shortfall


def _make_account(name: str, type: str, owner: str = "primary", allow_withdrawals: bool = True) -> Account:
    return Account(
        name=name,
        type=type,
        owner=owner,
        balance=0,
        cost_basis=0.0 if type == "taxable_brokerage" else None,
        growth_rate=0.0,
        dividend_yield=0.0,
        dividend_tax_treatment="plan_settings",
        reinvest_dividends=True,
        bond_allocation_percent=0,
        yearly_fees=0.0,
        allow_withdrawals=allow_withdrawals,
    )


def _make_strategy(order: list[str]) -> WithdrawalStrategy:
    return WithdrawalStrategy(
        order=[],
        account_specific_order=order,
        use_account_specific=True,
        rmd_satisfied_first=False,
    )


def test_skip_penalized_accounts_when_under_59_5():
    """Penalty-eligible accounts should be skipped when the owner is under 59.5."""
    cash = _make_account("Cash", "cash")
    ira = _make_account("IRA", "traditional_ira")
    brokerage = _make_account("Brokerage", "taxable_brokerage")

    accounts = {a.name: a for a in [cash, ira, brokerage]}
    # IRA listed first in strategy, but should be skipped due to penalty
    strategy = _make_strategy(["IRA", "Brokerage", "Cash"])

    balances = {"Cash": 0.0, "IRA": 50000.0, "Brokerage": 50000.0}
    cost_basis = {"Brokerage": CostBasisTracker(50000.0)}
    owner_ages = {"primary": 50.0}

    remaining, events, gains = cover_shortfall(
        shortfall=10000.0,
        balances=balances,
        accounts=accounts,
        strategy=strategy,
        cash_account_name="Cash",
        cost_basis=cost_basis,
        owner_ages=owner_ages,
    )

    assert remaining == 0.0
    assert len(events) == 1
    assert events[0].account == "Brokerage"
    assert events[0].amount == 10000.0
    # IRA should not have been touched
    assert balances["IRA"] == 50000.0
    assert balances["Brokerage"] == 40000.0


def test_penalized_accounts_used_as_last_resort():
    """When non-penalized accounts are insufficient, penalty-eligible accounts are used."""
    cash = _make_account("Cash", "cash")
    ira = _make_account("IRA", "traditional_ira")
    brokerage = _make_account("Brokerage", "taxable_brokerage")

    accounts = {a.name: a for a in [cash, ira, brokerage]}
    strategy = _make_strategy(["IRA", "Brokerage", "Cash"])

    balances = {"Cash": 0.0, "IRA": 50000.0, "Brokerage": 3000.0}
    cost_basis = {"Brokerage": CostBasisTracker(3000.0)}
    owner_ages = {"primary": 50.0}

    remaining, events, gains = cover_shortfall(
        shortfall=10000.0,
        balances=balances,
        accounts=accounts,
        strategy=strategy,
        cash_account_name="Cash",
        cost_basis=cost_basis,
        owner_ages=owner_ages,
    )

    assert remaining == 0.0
    assert len(events) == 2
    # First: brokerage (non-penalized)
    assert events[0].account == "Brokerage"
    assert events[0].amount == 3000.0
    # Second: IRA (penalized, last resort)
    assert events[1].account == "IRA"
    assert events[1].amount == 7000.0


def test_no_skip_when_over_59_5():
    """Accounts are not skipped when the owner is over 59.5."""
    cash = _make_account("Cash", "cash")
    ira = _make_account("IRA", "traditional_ira")
    brokerage = _make_account("Brokerage", "taxable_brokerage")

    accounts = {a.name: a for a in [cash, ira, brokerage]}
    strategy = _make_strategy(["IRA", "Brokerage", "Cash"])

    balances = {"Cash": 0.0, "IRA": 50000.0, "Brokerage": 50000.0}
    cost_basis = {"Brokerage": CostBasisTracker(50000.0)}
    owner_ages = {"primary": 65.0}

    remaining, events, gains = cover_shortfall(
        shortfall=10000.0,
        balances=balances,
        accounts=accounts,
        strategy=strategy,
        cash_account_name="Cash",
        cost_basis=cost_basis,
        owner_ages=owner_ages,
    )

    assert remaining == 0.0
    assert len(events) == 1
    # IRA used first per strategy order since no penalty applies
    assert events[0].account == "IRA"
    assert events[0].amount == 10000.0


def test_insolvency_when_all_accounts_empty():
    """Returns remaining shortfall when all accounts are exhausted."""
    cash = _make_account("Cash", "cash")
    ira = _make_account("IRA", "traditional_ira")

    accounts = {a.name: a for a in [cash, ira]}
    strategy = _make_strategy(["IRA", "Cash"])

    balances = {"Cash": 0.0, "IRA": 5000.0}
    cost_basis: dict[str, CostBasisTracker] = {}
    owner_ages = {"primary": 50.0}

    remaining, events, gains = cover_shortfall(
        shortfall=10000.0,
        balances=balances,
        accounts=accounts,
        strategy=strategy,
        cash_account_name="Cash",
        cost_basis=cost_basis,
        owner_ages=owner_ages,
    )

    assert remaining == 5000.0
    assert len(events) == 1
    assert events[0].account == "IRA"
    assert events[0].amount == 5000.0


def test_roth_ira_also_skipped_when_under_59_5():
    """Roth IRA should also be skipped for owners under 59.5."""
    cash = _make_account("Cash", "cash")
    roth = _make_account("Roth", "roth_ira")
    brokerage = _make_account("Brokerage", "taxable_brokerage")

    accounts = {a.name: a for a in [cash, roth, brokerage]}
    strategy = _make_strategy(["Roth", "Brokerage", "Cash"])

    balances = {"Cash": 0.0, "Roth": 50000.0, "Brokerage": 50000.0}
    cost_basis = {"Brokerage": CostBasisTracker(50000.0)}
    owner_ages = {"primary": 45.0}

    remaining, events, gains = cover_shortfall(
        shortfall=5000.0,
        balances=balances,
        accounts=accounts,
        strategy=strategy,
        cash_account_name="Cash",
        cost_basis=cost_basis,
        owner_ages=owner_ages,
    )

    assert remaining == 0.0
    assert len(events) == 1
    assert events[0].account == "Brokerage"
    assert balances["Roth"] == 50000.0
