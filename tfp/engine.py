"""Core month-by-month deterministic simulation engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .cost_basis import CostBasisTracker
from .real_assets import (
    RealAssetState,
    annual_to_monthly_rate,
    change_rate_for_year,
    mortgage_payment,
    property_tax_monthly,
    appreciate_asset,
)
from .schema import Account, Expense, Income, Plan
from .tax import YearIncomeSummary, compute_total_tax
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
class EngineResult:
    monthly: list[MonthResult]
    annual: list[AnnualResult]
    insolvency_years: list[int]


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


def run_deterministic(plan: Plan) -> EngineResult:
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

    months = _iter_months(plan_start, plan_end)

    for year, month, current_index in months:
        annual = annual_by_year.setdefault(year, AnnualResult(year=year))
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
        month_withdrawals = 0.0
        month_realized_cg = 0.0
        month_growth = 0.0
        month_dividends = 0.0
        month_fees = 0.0
        month_tax_settlement = 0.0
        month_taxable_ordinary_income = 0.0
        month_qualified_dividends = 0.0
        insolvent = False

        # Step 2/4: Income collection and withholding.
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
            month_income += amount
            income_by_name[income.name] = income_by_name.get(income.name, 0.0) + amount
            if income.tax_handling == "withhold" and income.withhold_percent is not None:
                month_taxable_ordinary_income += amount
                withheld = amount * income.withhold_percent
                balances[cash_account] -= withheld
                month_withheld += withheld

        # Step 5-7: Contributions and employer match.
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
            else:
                source_before = balances[source]
                balances[source] -= amount
                if accounts_by_name[source].type == "taxable_brokerage" and source in cost_basis:
                    month_realized_cg += cost_basis[source].withdraw(amount, source_before)
            balances[dest] += amount
            if accounts_by_name[dest].type == "taxable_brokerage" and dest in cost_basis:
                cost_basis[dest].add_basis(amount)
            month_contributions += amount

            if contribution.employer_match:
                salary_paid = income_by_name.get(contribution.employer_match.salary_reference, 0.0)
                match_cap = salary_paid * contribution.employer_match.up_to_percent_of_salary
                match_amount = min(amount, match_cap) * contribution.employer_match.match_percent
                if match_amount > 0:
                    balances[dest] += match_amount
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
            month_transfers += amount

            from_account = accounts_by_name[transfer.from_account]
            to_account = accounts_by_name[transfer.to_account]
            if from_account.type == "taxable_brokerage" and transfer.from_account in cost_basis:
                month_realized_cg += cost_basis[transfer.from_account].withdraw(amount, source_before)
            elif transfer.tax_treatment == "income":
                month_taxable_ordinary_income += amount
            if to_account.type == "taxable_brokerage" and transfer.to_account in cost_basis:
                cost_basis[transfer.to_account].add_basis(amount)

        # Steps 9-10 are Phase 4 (roth/rmd); reserved.

        # Step 11: Account growth.
        for account in plan.accounts:
            rate = annual_to_monthly_rate(account.growth_rate)
            growth = balances[account.name] * rate
            balances[account.name] += growth
            month_growth += growth

        # Step 12: Dividends.
        for account in plan.accounts:
            rate = annual_to_monthly_rate(account.dividend_yield)
            dividend = balances[account.name] * rate
            if dividend <= 0:
                continue
            month_dividends += dividend
            dividend_treatment = account.dividend_tax_treatment
            if dividend_treatment == "plan_settings":
                dividend_treatment = plan.plan_settings.default_dividend_tax_treatment
            if dividend_treatment == "income":
                month_taxable_ordinary_income += dividend
            elif dividend_treatment == "capital_gains":
                month_qualified_dividends += dividend
            if account.reinvest_dividends:
                balances[account.name] += dividend
                if account.type == "taxable_brokerage" and account.name in cost_basis:
                    cost_basis[account.name].add_basis(dividend)
            else:
                balances[cash_account] += dividend

        # Step 13: Fees.
        for account in plan.accounts:
            fee_rate = annual_to_monthly_rate(account.yearly_fees)
            fee = balances[account.name] * fee_rate
            if fee <= 0:
                continue
            balances[account.name] -= fee
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

            payment, _ = mortgage_payment(state)
            month_real_asset_expenses += payment

            for maintenance in state.asset.maintenance_expenses:
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
                gain = max(0.0, proceeds - state.asset.purchase_price)
                if txn.tax_treatment == "capital_gains":
                    month_realized_cg += gain
                elif txn.tax_treatment == "income":
                    month_taxable_ordinary_income += gain
                deposit = txn.deposit_to_account or cash_account
                balances[deposit] += proceeds
            elif txn.type == "buy_asset":
                balances[cash_account] -= (txn.amount + txn.fees)
            elif txn.type in {"transfer", "other"}:
                net = txn.amount - txn.fees
                if txn.deposit_to_account:
                    balances[txn.deposit_to_account] += net
                else:
                    balances[cash_account] += net

        # Step 16: Healthcare costs.
        for item in plan.healthcare.pre_medicare:
            start = item.start_date or "start"
            end = item.end_date or "end"
            if not _is_active(start, end, current_index, plan_start, plan_end):
                continue
            if owner_ages[item.owner] >= 65:
                continue
            factor = _amount_for_month(
                amount=1.0,
                change_over_time=item.change_over_time,
                change_rate=item.change_rate,
                inflation_rate=inflation_rate,
                current_year=year,
                plan_start=plan_start,
            )
            month_healthcare += (item.monthly_premium + item.annual_out_of_pocket / 12.0) * factor

        for item in plan.healthcare.post_medicare:
            start = item.medicare_start_date or "start"
            if not _is_active(start, "end", current_index, plan_start, plan_end):
                continue
            if owner_ages[item.owner] < 65:
                continue
            factor = _amount_for_month(
                amount=1.0,
                change_over_time=item.change_over_time,
                change_rate=item.change_rate,
                inflation_rate=inflation_rate,
                current_year=year,
                plan_start=plan_start,
            )
            monthly = (
                item.part_b_monthly_premium
                + item.supplement_monthly_premium
                + item.part_d_monthly_premium
                + item.annual_out_of_pocket / 12.0
            )
            month_healthcare += monthly * factor

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
                event_account = accounts_by_name[event.account]
                if event_account.type in {"401k", "traditional_ira"}:
                    month_taxable_ordinary_income += event.amount
            if remaining > 0:
                insolvent = True

        # Step 19: Expense payment from cash.
        balances[cash_account] -= total_expenses
        if balances[cash_account] < 0:
            insolvent = True

        # Step 20: cost basis updates are handled inline.
        # Step 21: Monthly recording and annual rollup.
        annual.income += month_income
        annual.tax_withheld += month_withheld
        annual.contributions += month_contributions
        annual.transfers += month_transfers
        annual.healthcare_expenses += month_healthcare
        annual.other_expenses += month_other_expenses
        annual.real_asset_expenses += month_real_asset_expenses
        annual.withdrawals += month_withdrawals
        annual.realized_capital_gains += month_realized_cg
        annual.growth += month_growth
        annual.dividends += month_dividends
        annual.fees += month_fees
        annual.taxable_ordinary_income += month_taxable_ordinary_income
        annual.qualified_dividends += month_qualified_dividends

        if month == 12:
            itemized = min(plan.tax_settings.itemized_deductions.salt_cap, max(0.0, annual.tax_state))
            itemized += max(0.0, plan.tax_settings.itemized_deductions.charitable_contributions)
            if plan.tax_settings.itemized_deductions.mortgage_interest_deductible:
                # Use a fixed share of real-asset expenses as a simple mortgage-interest proxy.
                itemized += max(0.0, annual.real_asset_expenses * 0.30)

            tax_result = compute_total_tax(
                YearIncomeSummary(
                    year=year,
                    filing_status=plan.filing_status,
                    state=plan.people.primary.state or "CA",
                    ordinary_income=annual.taxable_ordinary_income,
                    capital_gains=annual.realized_capital_gains,
                    qualified_dividends=annual.qualified_dividends,
                    investment_income=annual.realized_capital_gains + annual.qualified_dividends,
                    itemized_deductions=itemized,
                    withheld_tax=annual.tax_withheld,
                    early_withdrawal_penalty=0.0,
                ),
                plan.tax_settings,
                inflation_rate=inflation_rate,
            )
            annual.tax_federal = tax_result.federal_income_tax
            annual.tax_capital_gains = tax_result.capital_gains_tax
            annual.tax_state = tax_result.state_income_tax
            annual.tax_niit = tax_result.niit_tax
            annual.tax_amt = tax_result.amt_tax
            annual.tax_penalties = tax_result.early_withdrawal_penalty
            annual.tax_total = tax_result.total_tax

            settlement = tax_result.total_tax - annual.tax_withheld
            if settlement > 0:
                if balances[cash_account] < settlement:
                    remaining, events, gains = cover_shortfall(
                        shortfall=settlement - balances[cash_account],
                        balances=balances,
                        accounts=accounts_by_name,
                        strategy=plan.withdrawal_strategy,
                        cash_account_name=cash_account,
                        cost_basis=cost_basis,
                    )
                    extra_withdrawals = sum(e.amount for e in events)
                    month_withdrawals += extra_withdrawals
                    annual.withdrawals += extra_withdrawals
                    month_realized_cg += gains
                    annual.realized_capital_gains += gains
                    for event in events:
                        event_account = accounts_by_name[event.account]
                        if event_account.type in {"401k", "traditional_ira"}:
                            month_taxable_ordinary_income += event.amount
                            annual.taxable_ordinary_income += event.amount
                    if remaining > 0:
                        insolvent = True
                balances[cash_account] -= settlement
                annual.tax_payment = settlement
                month_tax_settlement = settlement
            else:
                refund = abs(settlement)
                balances[cash_account] += refund
                annual.tax_refund = refund
                month_tax_settlement = -refund

        net_worth_end = sum(max(0.0, bal) for bal in balances.values()) + sum(
            max(0.0, state.current_value) for state in real_asset_state.values()
        )
        if balances[cash_account] < 0:
            insolvent = True
        annual.net_worth_end = net_worth_end
        annual.insolvent = annual.insolvent or insolvent

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
        )
        monthly_results.append(month_result)

    annual_results = [annual_by_year[y] for y in sorted(annual_by_year)]
    insolvency_years = [row.year for row in annual_results if row.insolvent]
    return EngineResult(monthly=monthly_results, annual=annual_results, insolvency_years=insolvency_years)
