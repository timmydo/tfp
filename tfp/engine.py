"""Core month-by-month deterministic simulation engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .cost_basis import CostBasisTracker
from .healthcare import compute_monthly_healthcare_cost
from .real_assets import (
    RealAssetState,
    annual_to_monthly_rate,
    change_rate_for_year,
    mortgage_payment,
    property_tax_monthly,
    appreciate_asset,
)
from .rmd import execute_rmds
from .roth import execute_roth_conversions
from .schema import Account, Expense, Income, Plan
from .social_security import monthly_social_security_income
from .tax import YearIncomeSummary, compute_fica, compute_total_tax
from .withdrawals import cover_shortfall


@dataclass(slots=True)
class MonthResult:
    year: int
    month: int
    income: float
    tax_withheld: float
    contributions: float
    transfers: float
    healthcare_expenses: float
    other_expenses: float
    real_asset_expenses: float
    withdrawals: float
    realized_capital_gains: float
    growth: float
    dividends: float
    fees: float
    tax_settlement: float
    net_worth_end: float
    insolvent: bool
    account_balances_end: dict[str, float]
    withdrawal_sources: dict[str, float]


@dataclass(slots=True)
class AnnualResult:
    year: int
    income: float = 0.0
    tax_withheld: float = 0.0
    contributions: float = 0.0
    transfers: float = 0.0
    healthcare_expenses: float = 0.0
    other_expenses: float = 0.0
    real_asset_expenses: float = 0.0
    mortgage_interest_paid: float = 0.0
    withdrawals: float = 0.0
    realized_capital_gains: float = 0.0
    growth: float = 0.0
    dividends: float = 0.0
    fees: float = 0.0
    taxable_ordinary_income: float = 0.0
    qualified_dividends: float = 0.0
    tax_federal: float = 0.0
    tax_capital_gains: float = 0.0
    tax_state: float = 0.0
    tax_niit: float = 0.0
    tax_amt: float = 0.0
    tax_penalties: float = 0.0
    tax_total: float = 0.0
    tax_refund: float = 0.0
    tax_payment: float = 0.0
    net_worth_end: float = 0.0
    insolvent: bool = False


@dataclass(slots=True)
class AccountAnnualDetail:
    year: int
    account: str
    starting_balance: float = 0.0
    contributions: float = 0.0
    withdrawals: float = 0.0
    growth: float = 0.0
    dividends: float = 0.0
    fees: float = 0.0
    ending_balance: float = 0.0


@dataclass(slots=True)
class EngineResult:
    monthly: list[MonthResult]
    annual: list[AnnualResult]
    insolvency_years: list[int]
    account_annual: dict[str, list[AccountAnnualDetail]]
    withdrawal_sources_by_year: dict[int, dict[str, float]]


def _parse_ym(value: str) -> tuple[int, int]:
    dt = datetime.strptime(value, "%Y-%m")
    return dt.year, dt.month


def _date_index(value: str, plan_start: str, plan_end: str) -> int:
    if value == "start":
        value = plan_start
    elif value == "end":
        value = plan_end
    year, month = _parse_ym(value)
    return year * 12 + month


def _iter_months(start: str, end: str) -> list[tuple[int, int, int]]:
    sy, sm = _parse_ym(start)
    ey, em = _parse_ym(end)
    current_y, current_m = sy, sm
    out: list[tuple[int, int, int]] = []
    while (current_y < ey) or (current_y == ey and current_m <= em):
        idx = current_y * 12 + current_m
        out.append((current_y, current_m, idx))
        current_m += 1
        if current_m > 12:
            current_m = 1
            current_y += 1
    return out


def _is_active(start_date: str, end_date: str, current_index: int, plan_start: str, plan_end: str) -> bool:
    start_idx = _date_index(start_date, plan_start, plan_end)
    end_idx = _date_index(end_date, plan_start, plan_end)
    return start_idx <= current_index <= end_idx


def _occurs_this_month(
    *,
    frequency: str,
    start_date: str,
    end_date: str,
    current_year: int,
    current_month: int,
    current_index: int,
    plan_start: str,
    plan_end: str,
) -> bool:
    if not _is_active(start_date, end_date, current_index, plan_start, plan_end):
        return False

    start_year, start_month = _parse_ym(plan_start if start_date == "start" else start_date)
    start_index = start_year * 12 + start_month

    if frequency == "monthly":
        return True
    if frequency == "annual":
        return current_month == ((start_index - 1) % 12) + 1
    if frequency == "one_time":
        return current_index == start_index
    return False


def _change_multiplier(
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


def _amount_for_month(
    *,
    amount: float,
    change_over_time: str,
    change_rate: float | None,
    inflation_rate: float,
    current_year: int,
    plan_start: str,
) -> float:
    start_year, _ = _parse_ym(plan_start)
    years_elapsed = max(0, current_year - start_year)
    return amount * _change_multiplier(
        change_over_time=change_over_time,
        change_rate=change_rate,
        inflation_rate=inflation_rate,
        years_elapsed=years_elapsed,
    )


def _age_years_at_month(birthday_ym: str, year: int, month: int) -> float:
    by, bm = _parse_ym(birthday_ym)
    months = (year - by) * 12 + (month - bm)
    return max(0.0, months / 12.0)


def _pick_cash_account(accounts: list[Account]) -> str:
    for account in accounts:
        if account.type == "cash":
            return account.name
    raise ValueError("at least one cash account is required")


def _primary_residence_exclusion(filing_status: str) -> float:
    if filing_status == "married_filing_jointly":
        return 500_000.0
    return 250_000.0


def _active_income_items(
    items: list[Income],
    *,
    current_year: int,
    current_month: int,
    current_index: int,
    plan_start: str,
    plan_end: str,
) -> list[Income]:
    out: list[Income] = []
    for item in items:
        if _occurs_this_month(
            frequency=item.frequency,
            start_date=item.start_date,
            end_date=item.end_date,
            current_year=current_year,
            current_month=current_month,
            current_index=current_index,
            plan_start=plan_start,
            plan_end=plan_end,
        ):
            out.append(item)
    return out


def _active_expense_items(
    items: list[Expense],
    *,
    current_year: int,
    current_month: int,
    current_index: int,
    plan_start: str,
    plan_end: str,
) -> list[Expense]:
    out: list[Expense] = []
    for item in items:
        if _occurs_this_month(
            frequency=item.frequency,
            start_date=item.start_date,
            end_date=item.end_date,
            current_year=current_year,
            current_month=current_month,
            current_index=current_index,
            plan_start=plan_start,
            plan_end=plan_end,
        ):
            out.append(item)
    return out


def run_deterministic(
    plan: Plan,
    annual_return_overrides: dict[int, tuple[float, float]] | None = None,
) -> EngineResult:
    plan_start = plan.plan_settings.plan_start
    plan_end = plan.plan_settings.plan_end
    inflation_rate = plan.plan_settings.inflation_rate

    accounts_by_name = {a.name: a for a in plan.accounts}
    balances = {a.name: float(a.balance) for a in plan.accounts}
    cash_account = _pick_cash_account(plan.accounts)

    cost_basis = {
        account.name: CostBasisTracker(total_basis=float(account.cost_basis or 0.0))
        for account in plan.accounts
        if account.type == "taxable_brokerage"
    }

    real_asset_state = {
        asset.name: RealAssetState(
            asset=asset,
            current_value=float(asset.current_value),
            mortgage_balance=float(asset.mortgage.remaining_balance) if asset.mortgage else 0.0,
        )
        for asset in plan.real_assets
    }

    monthly_results: list[MonthResult] = []
    annual_by_year: dict[int, AnnualResult] = {}
    account_annual_by_year: dict[int, dict[str, AccountAnnualDetail]] = {}
    withdrawal_sources_by_year: dict[int, dict[str, float]] = {}

    months = _iter_months(plan_start, plan_end)
    prior_year_end_balances = {name: balance for name, balance in balances.items()}
    irmaa_magi_history: dict[int, float] = {}
    early_withdrawal_penalties: dict[int, float] = {}
    annual_fica_withheld: dict[int, float] = {}
    roth_contribution_basis = {
        account.name: max(0.0, float(account.balance))
        for account in plan.accounts
        if account.type == "roth_ira"
    }

    def _year_account_detail(target_year: int, account_name: str) -> AccountAnnualDetail:
        year_map = account_annual_by_year.setdefault(target_year, {})
        detail = year_map.get(account_name)
        if detail is None:
            detail = AccountAnnualDetail(
                year=target_year,
                account=account_name,
                starting_balance=max(0.0, balances.get(account_name, 0.0)),
                ending_balance=max(0.0, balances.get(account_name, 0.0)),
            )
            year_map[account_name] = detail
        return detail

    def _add_contribution(target_year: int, account_name: str, amount: float) -> None:
        if amount <= 0:
            return
        _year_account_detail(target_year, account_name).contributions += amount

    def _add_withdrawal(target_year: int, account_name: str, amount: float) -> None:
        if amount <= 0:
            return
        _year_account_detail(target_year, account_name).withdrawals += amount

    def _add_withdrawal_source(target_year: int, account_name: str, amount: float) -> None:
        if amount <= 0:
            return
        source_map = withdrawal_sources_by_year.setdefault(target_year, {})
        source_map[account_name] = source_map.get(account_name, 0.0) + amount

    def _record_roth_basis_contribution(account_name: str, amount: float) -> None:
        if amount <= 0 or account_name not in roth_contribution_basis:
            return
        roth_contribution_basis[account_name] += amount

    def _handle_early_withdrawal_effects(
        *,
        account: Account,
        amount: float,
        owner_ages: dict[str, float],
    ) -> tuple[float, float]:
        """Return (ordinary_income_added, early_penalty_added) for a withdrawal event."""
        if amount <= 0:
            return 0.0, 0.0
        owner_age = owner_ages.get(account.owner, 0.0)
        if account.type in {"401k", "traditional_ira"}:
            penalty = amount * 0.10 if owner_age < 59.5 else 0.0
            return amount, penalty
        if account.type == "roth_ira":
            basis = roth_contribution_basis.get(account.name, 0.0)
            earnings_withdrawn = max(0.0, amount - basis)
            roth_contribution_basis[account.name] = max(0.0, basis - amount)
            if owner_age < 59.5:
                return 0.0, earnings_withdrawn * 0.10
        return 0.0, 0.0

    ytd_wages_by_owner = {"primary": 0.0, "spouse": 0.0}

    for year, month, current_index in months:
        # Step 1: Age calculation.
        annual = annual_by_year.setdefault(year, AnnualResult(year=year))
        annual_fica_withheld.setdefault(year, 0.0)
        if month == 1:
            ytd_wages_by_owner = {"primary": 0.0, "spouse": 0.0}
        for account in plan.accounts:
            _year_account_detail(year, account.name)
        owner_ages = {
            "primary": _age_years_at_month(plan.people.primary.birthday, year, month),
            "spouse": _age_years_at_month(plan.people.spouse.birthday, year, month) if plan.people.spouse else 0.0,
        }

        month_income = 0.0
        month_withheld = 0.0
        month_contributions = 0.0
        month_transfers = 0.0
        month_healthcare = 0.0
        month_other_expenses = 0.0
        month_real_asset_expenses = 0.0
        month_mortgage_interest = 0.0
        month_withdrawals = 0.0
        month_realized_cg = 0.0
        month_growth = 0.0
        month_dividends = 0.0
        month_fees = 0.0
        month_tax_settlement = 0.0
        month_taxable_ordinary_income = 0.0
        month_qualified_dividends = 0.0
        insolvent = False
        month_withdrawal_sources: dict[str, float] = {}
        early_withdrawal_penalties.setdefault(year, 0.0)

        # Step 2: Income collection.
        income_by_name: dict[str, float] = {}
        for income in _active_income_items(
            plan.income,
            current_year=year,
            current_month=month,
            current_index=current_index,
            plan_start=plan_start,
            plan_end=plan_end,
        ):
            amount = _amount_for_month(
                amount=income.amount,
                change_over_time=income.change_over_time,
                change_rate=income.change_rate,
                inflation_rate=inflation_rate,
                current_year=year,
                plan_start=plan_start,
            )
            balances[cash_account] += amount
            _add_contribution(year, cash_account, amount)
            month_income += amount
            income_by_name[income.name] = income_by_name.get(income.name, 0.0) + amount

            # Step 3-4: FICA withholding and income tax withholding.
            if income.tax_handling == "withhold" and income.withhold_percent is not None:
                month_taxable_ordinary_income += amount
                fica_withheld = compute_fica(
                    wages=amount,
                    ytd_wages=ytd_wages_by_owner.get(income.owner, 0.0),
                    year=year,
                    inflation_rate=inflation_rate,
                    filing_status=plan.filing_status,
                )
                ytd_wages_by_owner[income.owner] = ytd_wages_by_owner.get(income.owner, 0.0) + amount
                annual_fica_withheld[year] += fica_withheld

                income_tax_withheld = amount * income.withhold_percent
                withheld = fica_withheld + income_tax_withheld
                balances[cash_account] -= withheld
                _add_withdrawal(year, cash_account, withheld)
                month_withheld += withheld

        # Step 2: Social Security income collection.
        ss_income, _ = monthly_social_security_income(
            entries=plan.social_security,
            owner_ages=owner_ages,
            inflation_rate=inflation_rate,
        )
        if ss_income > 0:
            balances[cash_account] += ss_income
            _add_contribution(year, cash_account, ss_income)
            month_income += ss_income
            # v1 simplification: estimate 85% of SS benefits as taxable.
            month_taxable_ordinary_income += ss_income * 0.85

        # Steps 5-7: Payroll deductions, employer match deposits, other contributions.
        for contribution in plan.contributions:
            if not _occurs_this_month(
                frequency=contribution.frequency,
                start_date=contribution.start_date,
                end_date=contribution.end_date,
                current_year=year,
                current_month=month,
                current_index=current_index,
                plan_start=plan_start,
                plan_end=plan_end,
            ):
                continue

            amount = _amount_for_month(
                amount=contribution.amount,
                change_over_time=contribution.change_over_time,
                change_rate=contribution.change_rate,
                inflation_rate=inflation_rate,
                current_year=year,
                plan_start=plan_start,
            )

            source = contribution.source_account
            dest = contribution.destination_account
            if source == "income":
                balances[cash_account] -= amount
                _add_withdrawal(year, cash_account, amount)
            else:
                source_before = balances[source]
                balances[source] -= amount
                _add_withdrawal(year, source, amount)
                if accounts_by_name[source].type == "taxable_brokerage" and source in cost_basis:
                    month_realized_cg += cost_basis[source].withdraw(amount, source_before)
            balances[dest] += amount
            _add_contribution(year, dest, amount)
            _record_roth_basis_contribution(dest, amount)
            if accounts_by_name[dest].type == "taxable_brokerage" and dest in cost_basis:
                cost_basis[dest].add_basis(amount)
            month_contributions += amount

            if contribution.employer_match:
                salary_paid = income_by_name.get(contribution.employer_match.salary_reference, 0.0)
                match_cap = salary_paid * contribution.employer_match.up_to_percent_of_salary
                match_amount = min(amount, match_cap) * contribution.employer_match.match_percent
                if match_amount > 0:
                    balances[dest] += match_amount
                    _add_contribution(year, dest, match_amount)
                    _record_roth_basis_contribution(dest, match_amount)
                    if accounts_by_name[dest].type == "taxable_brokerage" and dest in cost_basis:
                        cost_basis[dest].add_basis(match_amount)
                    month_contributions += match_amount

        # Step 8: Recurring transfers.
        for transfer in plan.transfers:
            if not _occurs_this_month(
                frequency=transfer.frequency,
                start_date=transfer.start_date,
                end_date=transfer.end_date,
                current_year=year,
                current_month=month,
                current_index=current_index,
                plan_start=plan_start,
                plan_end=plan_end,
            ):
                continue

            amount = transfer.amount
            source_before = balances[transfer.from_account]
            balances[transfer.from_account] -= amount
            balances[transfer.to_account] += amount
            _add_withdrawal(year, transfer.from_account, amount)
            _add_contribution(year, transfer.to_account, amount)
            _record_roth_basis_contribution(transfer.to_account, amount)
            month_transfers += amount

            from_account = accounts_by_name[transfer.from_account]
            to_account = accounts_by_name[transfer.to_account]
            if from_account.type == "taxable_brokerage" and transfer.from_account in cost_basis:
                month_realized_cg += cost_basis[transfer.from_account].withdraw(amount, source_before)
            elif transfer.tax_treatment == "income":
                month_taxable_ordinary_income += amount
            if to_account.type == "taxable_brokerage" and transfer.to_account in cost_basis:
                cost_basis[transfer.to_account].add_basis(amount)

        # Step 9 / Step 10: Roth conversions and RMD processing.
        if month == 12 and plan.withdrawal_strategy.rmd_satisfied_first:
            rmd_destination = plan.rmds.destination_account or cash_account
            rmd_before = {
                name: balances.get(name, 0.0)
                for name in set(plan.rmds.accounts + [rmd_destination])
            }
            rmd_withdrawn, rmd_ordinary_income = execute_rmds(
                settings=plan.rmds,
                accounts_by_name=accounts_by_name,
                balances=balances,
                prior_year_end_balances=prior_year_end_balances,
                owner_ages=owner_ages,
            )
            if rmd_withdrawn > 0:
                for account_name in plan.rmds.accounts:
                    before = rmd_before.get(account_name, 0.0)
                    after = balances.get(account_name, 0.0)
                    withdrawn = max(0.0, before - after)
                    if withdrawn > 0:
                        _add_withdrawal(year, account_name, withdrawn)
                        _add_withdrawal_source(year, account_name, withdrawn)
                        month_withdrawal_sources[account_name] = month_withdrawal_sources.get(account_name, 0.0) + withdrawn
                deposited = max(0.0, balances.get(rmd_destination, 0.0) - rmd_before.get(rmd_destination, 0.0))
                if deposited > 0:
                    _add_contribution(year, rmd_destination, deposited)
                    _record_roth_basis_contribution(rmd_destination, deposited)
            month_withdrawals += rmd_withdrawn
            month_taxable_ordinary_income += rmd_ordinary_income

        roth_accounts = {c.from_account for c in plan.roth_conversions} | {c.to_account for c in plan.roth_conversions}
        roth_before = {name: balances.get(name, 0.0) for name in roth_accounts}
        roth_amount, roth_ordinary_income = execute_roth_conversions(
            conversions=plan.roth_conversions,
            balances=balances,
            current_year=year,
            current_month=month,
            current_index=current_index,
            plan_start=plan_start,
            plan_end=plan_end,
            filing_status=plan.filing_status,
            inflation_rate=inflation_rate,
            ytd_taxable_ordinary_income=annual.taxable_ordinary_income + month_taxable_ordinary_income,
        )
        if roth_amount > 0:
            for name in roth_accounts:
                before = roth_before.get(name, 0.0)
                after = balances.get(name, 0.0)
                delta = after - before
                if delta > 0:
                    _add_contribution(year, name, delta)
                    _record_roth_basis_contribution(name, delta)
                elif delta < 0:
                    _add_withdrawal(year, name, abs(delta))
        month_transfers += roth_amount
        month_taxable_ordinary_income += roth_ordinary_income

        if month == 12 and not plan.withdrawal_strategy.rmd_satisfied_first:
            rmd_destination = plan.rmds.destination_account or cash_account
            rmd_before = {
                name: balances.get(name, 0.0)
                for name in set(plan.rmds.accounts + [rmd_destination])
            }
            rmd_withdrawn, rmd_ordinary_income = execute_rmds(
                settings=plan.rmds,
                accounts_by_name=accounts_by_name,
                balances=balances,
                prior_year_end_balances=prior_year_end_balances,
                owner_ages=owner_ages,
            )
            if rmd_withdrawn > 0:
                for account_name in plan.rmds.accounts:
                    before = rmd_before.get(account_name, 0.0)
                    after = balances.get(account_name, 0.0)
                    withdrawn = max(0.0, before - after)
                    if withdrawn > 0:
                        _add_withdrawal(year, account_name, withdrawn)
                        _add_withdrawal_source(year, account_name, withdrawn)
                        month_withdrawal_sources[account_name] = month_withdrawal_sources.get(account_name, 0.0) + withdrawn
                deposited = max(0.0, balances.get(rmd_destination, 0.0) - rmd_before.get(rmd_destination, 0.0))
                if deposited > 0:
                    _add_contribution(year, rmd_destination, deposited)
                    _record_roth_basis_contribution(rmd_destination, deposited)
            month_withdrawals += rmd_withdrawn
            month_taxable_ordinary_income += rmd_ordinary_income

        # Step 11: Account growth.
        for account in plan.accounts:
            annual_growth_rate = account.growth_rate
            if annual_return_overrides and year in annual_return_overrides:
                stock_return, bond_return = annual_return_overrides[year]
                bond_weight = max(0.0, min(100.0, account.bond_allocation_percent)) / 100.0
                stock_weight = 1.0 - bond_weight
                annual_growth_rate = (stock_return * stock_weight) + (bond_return * bond_weight)
            rate = annual_to_monthly_rate(annual_growth_rate)
            growth = balances[account.name] * rate
            balances[account.name] += growth
            _year_account_detail(year, account.name).growth += growth
            month_growth += growth

        # Step 12: Dividends.
        for account in plan.accounts:
            rate = annual_to_monthly_rate(account.dividend_yield)
            dividend = balances[account.name] * rate
            if dividend <= 0:
                continue
            month_dividends += dividend
            _year_account_detail(year, account.name).dividends += dividend
            dividend_treatment = account.dividend_tax_treatment
            if dividend_treatment == "plan_settings":
                dividend_treatment = plan.plan_settings.default_dividend_tax_treatment
            if dividend_treatment == "income":
                month_taxable_ordinary_income += dividend
            elif dividend_treatment == "capital_gains":
                month_qualified_dividends += dividend
            if account.reinvest_dividends:
                balances[account.name] += dividend
                _add_contribution(year, account.name, dividend)
                if account.type == "taxable_brokerage" and account.name in cost_basis:
                    cost_basis[account.name].add_basis(dividend)
            else:
                balances[cash_account] += dividend
                _add_contribution(year, cash_account, dividend)

        # Step 13: Fees.
        for account in plan.accounts:
            fee_rate = annual_to_monthly_rate(account.yearly_fees)
            fee = balances[account.name] * fee_rate
            if fee <= 0:
                continue
            balances[account.name] -= fee
            _year_account_detail(year, account.name).fees += fee
            _add_withdrawal(year, account.name, fee)
            month_fees += fee

        # Step 14: Real asset updates.
        for state in real_asset_state.values():
            annual_rate = change_rate_for_year(
                state.asset.change_over_time,
                state.asset.change_rate,
                inflation_rate,
            )
            appreciate_asset(state, annual_rate)
            month_real_asset_expenses += property_tax_monthly(state)

            payment, _, interest = mortgage_payment(state)
            month_real_asset_expenses += payment
            month_mortgage_interest += interest

            for maintenance in state.asset.maintenance_expenses:
                # v1 simplification: maintenance amounts are fixed nominal dollars.
                if maintenance.frequency == "monthly":
                    month_real_asset_expenses += maintenance.amount
                elif maintenance.frequency == "annual" and month == 1:
                    month_real_asset_expenses += maintenance.amount

        # Step 15: One-time transactions.
        for txn in plan.transactions:
            txn_idx = _date_index(txn.date, plan_start, plan_end)
            if txn_idx != current_index:
                continue

            if txn.type == "sell_asset" and txn.linked_asset and txn.linked_asset in real_asset_state:
                state = real_asset_state.pop(txn.linked_asset)
                proceeds = max(0.0, txn.amount - txn.fees)
                basis = state.asset.purchase_price or 0.0
                gain = max(0.0, proceeds - basis)
                if state.asset.primary_residence:
                    exclusion = _primary_residence_exclusion(plan.filing_status)
                    gain = max(0.0, gain - exclusion)
                if txn.tax_treatment == "capital_gains":
                    month_realized_cg += gain
                elif txn.tax_treatment == "income":
                    month_taxable_ordinary_income += gain
                deposit = txn.deposit_to_account or cash_account
                balances[deposit] += proceeds
                _add_contribution(year, deposit, proceeds)
                _record_roth_basis_contribution(deposit, proceeds)
            elif txn.type == "buy_asset":
                balances[cash_account] -= (txn.amount + txn.fees)
                _add_withdrawal(year, cash_account, txn.amount + txn.fees)
            elif txn.type in {"transfer", "other"}:
                net = txn.amount - txn.fees
                if txn.deposit_to_account:
                    balances[txn.deposit_to_account] += net
                    _add_contribution(year, txn.deposit_to_account, net)
                    _record_roth_basis_contribution(txn.deposit_to_account, net)
                else:
                    balances[cash_account] += net
                    _add_contribution(year, cash_account, net)

        # Step 16: Healthcare costs (including IRMAA surcharges when enabled).
        month_healthcare, _ = compute_monthly_healthcare_cost(
            healthcare=plan.healthcare,
            owner_ages=owner_ages,
            current_year=year,
            current_index=current_index,
            plan_start=plan_start,
            plan_end=plan_end,
            inflation_rate=inflation_rate,
            filing_status=plan.filing_status,
            irmaa_magi_history=irmaa_magi_history,
        )

        # Step 17: Non-healthcare expenses.
        for expense in _active_expense_items(
            plan.expenses,
            current_year=year,
            current_month=month,
            current_index=current_index,
            plan_start=plan_start,
            plan_end=plan_end,
        ):
            amount = _amount_for_month(
                amount=expense.amount,
                change_over_time=expense.change_over_time,
                change_rate=expense.change_rate,
                inflation_rate=inflation_rate,
                current_year=year,
                plan_start=plan_start,
            )
            month_other_expenses += amount

        # Step 18: Shortfall detection and withdrawals.
        total_expenses = month_healthcare + month_other_expenses + month_real_asset_expenses
        if balances[cash_account] < total_expenses:
            remaining, events, gains = cover_shortfall(
                shortfall=total_expenses - balances[cash_account],
                balances=balances,
                accounts=accounts_by_name,
                strategy=plan.withdrawal_strategy,
                cash_account_name=cash_account,
                cost_basis=cost_basis,
            )
            month_withdrawals += sum(e.amount for e in events)
            month_realized_cg += gains
            for event in events:
                _add_withdrawal(year, event.account, event.amount)
                _add_withdrawal_source(year, event.account, event.amount)
                month_withdrawal_sources[event.account] = month_withdrawal_sources.get(event.account, 0.0) + event.amount
                _add_contribution(year, cash_account, event.amount)
                event_account = accounts_by_name[event.account]
                ordinary_income, penalty = _handle_early_withdrawal_effects(
                    account=event_account,
                    amount=event.amount,
                    owner_ages=owner_ages,
                )
                month_taxable_ordinary_income += ordinary_income
                early_withdrawal_penalties[year] += penalty
            if remaining > 0:
                insolvent = True

        # Step 19: Expense payment from cash.
        balances[cash_account] -= total_expenses
        _add_withdrawal(year, cash_account, total_expenses)
        if balances[cash_account] < 0:
            insolvent = True

        # Step 20: Cost basis updates are handled inline.
        # Step 21: Monthly recording and annual rollup.
        annual.income += month_income
        annual.tax_withheld += month_withheld
        annual.contributions += month_contributions
        annual.transfers += month_transfers
        annual.healthcare_expenses += month_healthcare
        annual.other_expenses += month_other_expenses
        annual.real_asset_expenses += month_real_asset_expenses
        annual.mortgage_interest_paid += month_mortgage_interest
        annual.withdrawals += month_withdrawals
        annual.realized_capital_gains += month_realized_cg
        annual.growth += month_growth
        annual.dividends += month_dividends
        annual.fees += month_fees
        annual.taxable_ordinary_income += month_taxable_ordinary_income
        annual.qualified_dividends += month_qualified_dividends

        if month == 12:
            annual.tax_refund = 0.0
            annual.tax_payment = 0.0
            estimated_state_tax = max(0.0, annual.tax_state)
            settlement = 0.0
            tax_result = None

            # Additional tax-payment withdrawals can increase taxable income.
            # Recompute tax until settlement stabilizes or no more withdrawals are possible.
            for _ in range(8):
                itemized = min(plan.tax_settings.itemized_deductions.salt_cap, estimated_state_tax)
                itemized += max(0.0, plan.tax_settings.itemized_deductions.charitable_contributions)
                if plan.tax_settings.itemized_deductions.mortgage_interest_deductible:
                    itemized += max(0.0, annual.mortgage_interest_paid)

                tax_result = compute_total_tax(
                    YearIncomeSummary(
                        year=year,
                        filing_status=plan.filing_status,
                        state=plan.people.primary.state or "CA",
                        ordinary_income=annual.taxable_ordinary_income,
                        capital_gains=annual.realized_capital_gains,
                        qualified_dividends=annual.qualified_dividends,
                        investment_income=0.0,
                        itemized_deductions=itemized,
                        withheld_tax=annual.tax_withheld,
                        early_withdrawal_penalty=early_withdrawal_penalties[year],
                    ),
                    plan.tax_settings,
                    inflation_rate=inflation_rate,
                )
                estimated_state_tax = max(0.0, tax_result.state_income_tax)
                settlement = (tax_result.total_tax + annual_fica_withheld[year]) - annual.tax_withheld
                if settlement <= 0 or balances[cash_account] >= settlement:
                    break

                remaining, events, gains = cover_shortfall(
                    shortfall=settlement - balances[cash_account],
                    balances=balances,
                    accounts=accounts_by_name,
                    strategy=plan.withdrawal_strategy,
                    cash_account_name=cash_account,
                    cost_basis=cost_basis,
                )
                extra_withdrawals = sum(e.amount for e in events)
                if extra_withdrawals <= 0:
                    if remaining > 0:
                        insolvent = True
                    break

                month_withdrawals += extra_withdrawals
                annual.withdrawals += extra_withdrawals
                month_realized_cg += gains
                annual.realized_capital_gains += gains
                for event in events:
                    _add_withdrawal(year, event.account, event.amount)
                    _add_withdrawal_source(year, event.account, event.amount)
                    month_withdrawal_sources[event.account] = month_withdrawal_sources.get(event.account, 0.0) + event.amount
                    _add_contribution(year, cash_account, event.amount)
                    event_account = accounts_by_name[event.account]
                    ordinary_income, penalty = _handle_early_withdrawal_effects(
                        account=event_account,
                        amount=event.amount,
                        owner_ages=owner_ages,
                    )
                    month_taxable_ordinary_income += ordinary_income
                    annual.taxable_ordinary_income += ordinary_income
                    early_withdrawal_penalties[year] += penalty
                if remaining > 0:
                    insolvent = True
                    break

            if tax_result is None:
                raise RuntimeError("tax_result not computed for year-end settlement")

            annual.tax_federal = tax_result.federal_income_tax
            annual.tax_capital_gains = tax_result.capital_gains_tax
            annual.tax_state = tax_result.state_income_tax
            annual.tax_niit = tax_result.niit_tax
            annual.tax_amt = tax_result.amt_tax
            annual.tax_penalties = tax_result.early_withdrawal_penalty
            annual.tax_total = tax_result.total_tax + annual_fica_withheld[year]

            if settlement > 0:
                balances[cash_account] -= settlement
                _add_withdrawal(year, cash_account, settlement)
                annual.tax_payment = settlement
                month_tax_settlement = settlement
            else:
                refund = abs(settlement)
                balances[cash_account] += refund
                _add_contribution(year, cash_account, refund)
                annual.tax_refund = refund
                month_tax_settlement = -refund

            irmaa_magi_history[year] = max(
                0.0,
                annual.taxable_ordinary_income + annual.realized_capital_gains + annual.qualified_dividends,
            )
            prior_year_end_balances = {name: max(0.0, balance) for name, balance in balances.items()}

        net_worth_end = sum(max(0.0, bal) for bal in balances.values()) + sum(
            max(0.0, state.current_value) for state in real_asset_state.values()
        )
        if balances[cash_account] < 0:
            insolvent = True
        annual.net_worth_end = net_worth_end
        annual.insolvent = annual.insolvent or insolvent
        for account_name in balances:
            _year_account_detail(year, account_name).ending_balance = max(0.0, balances[account_name])

        month_result = MonthResult(
            year=year,
            month=month,
            income=month_income,
            tax_withheld=month_withheld,
            contributions=month_contributions,
            transfers=month_transfers,
            healthcare_expenses=month_healthcare,
            other_expenses=month_other_expenses,
            real_asset_expenses=month_real_asset_expenses,
            withdrawals=month_withdrawals,
            realized_capital_gains=month_realized_cg,
            growth=month_growth,
            dividends=month_dividends,
            fees=month_fees,
            tax_settlement=month_tax_settlement,
            net_worth_end=net_worth_end,
            insolvent=insolvent,
            account_balances_end={name: max(0.0, value) for name, value in balances.items()},
            withdrawal_sources=month_withdrawal_sources,
        )
        monthly_results.append(month_result)

    annual_results = [annual_by_year[y] for y in sorted(annual_by_year)]
    insolvency_years = [row.year for row in annual_results if row.insolvent]
    account_annual: dict[str, list[AccountAnnualDetail]] = {}
    for year in sorted(account_annual_by_year):
        for account_name, detail in account_annual_by_year[year].items():
            account_annual.setdefault(account_name, []).append(detail)
    return EngineResult(
        monthly=monthly_results,
        annual=annual_results,
        insolvency_years=insolvency_years,
        account_annual=account_annual,
        withdrawal_sources_by_year=withdrawal_sources_by_year,
    )
