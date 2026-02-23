"""Chart payload generation for the self-contained report."""

from __future__ import annotations

from .engine import EngineResult
from .schema import Account, Plan
from .simulation import SimulationResult


def _account_year_end(engine_result: EngineResult, account_name: str, year: int) -> float:
    for detail in engine_result.account_annual.get(account_name, []):
        if detail.year == year:
            return detail.ending_balance
    return 0.0


def _stacked_by_account(plan: Plan, engine_result: EngineResult, years: list[int]) -> dict[str, list[float]]:
    data: dict[str, list[float]] = {account.name: [] for account in plan.accounts}
    for year in years:
        for account in plan.accounts:
            data[account.name].append(_account_year_end(engine_result, account.name, year))
    return data


def _allocation_series(plan: Plan, engine_result: EngineResult, years: list[int]) -> dict[str, list[float]]:
    stocks: list[float] = []
    bonds: list[float] = []
    cash: list[float] = []
    for year in years:
        stock_total = 0.0
        bond_total = 0.0
        cash_total = 0.0
        for account in plan.accounts:
            balance = _account_year_end(engine_result, account.name, year)
            if account.type == "cash":
                cash_total += balance
                continue
            bond_weight = max(0.0, min(100.0, account.bond_allocation_percent)) / 100.0
            bond_total += balance * bond_weight
            stock_total += balance * (1.0 - bond_weight)
        stocks.append(stock_total)
        bonds.append(bond_total)
        cash.append(cash_total)
    return {"stocks": stocks, "bonds": bonds, "cash": cash}


def _annual_tax_stacks(engine_result: EngineResult, years: list[int]) -> dict[str, list[float]]:
    by_year = {row.year: row for row in engine_result.annual}

    def _series(key: str) -> list[float]:
        out: list[float] = []
        for year in years:
            row = by_year.get(year)
            out.append(float(getattr(row, key, 0.0)) if row else 0.0)
        return out

    return {
        "federal": _series("tax_federal"),
        "state": _series("tax_state"),
        "capital_gains": _series("tax_capital_gains"),
        "niit": _series("tax_niit"),
        "amt": _series("tax_amt"),
        "penalties": _series("tax_penalties"),
    }


def _withdrawal_sources(engine_result: EngineResult, years: list[int]) -> dict[str, list[float]]:
    names = sorted({name for by_account in engine_result.withdrawal_sources_by_year.values() for name in by_account})
    data = {name: [0.0 for _ in years] for name in names}
    year_to_idx = {year: idx for idx, year in enumerate(years)}
    for year, by_account in engine_result.withdrawal_sources_by_year.items():
        idx = year_to_idx.get(year)
        if idx is None:
            continue
        for name, amount in by_account.items():
            if name in data:
                data[name][idx] = amount
    return data


def _account_flow_by_year(plan: Plan, engine_result: EngineResult, years: list[int]) -> dict[str, list[float]]:
    data: dict[str, list[float]] = {account.name: [0.0 for _ in years] for account in plan.accounts}
    year_to_idx = {year: idx for idx, year in enumerate(years)}
    prev_balances = {account.name: float(account.balance) for account in plan.accounts}

    for month in engine_result.monthly:
        year_idx = year_to_idx.get(month.year)
        if year_idx is None:
            continue
        for account in plan.accounts:
            name = account.name
            current = float(month.account_balances_end.get(name, 0.0))
            delta = current - prev_balances.get(name, 0.0)
            data[name][year_idx] += delta
            prev_balances[name] = current
    return data


def _expense_breakdown(engine_result: EngineResult, years: list[int]) -> dict[str, list[float]]:
    by_year = {row.year: row for row in engine_result.annual}
    healthcare: list[float] = []
    other: list[float] = []
    real_assets: list[float] = []
    for year in years:
        row = by_year.get(year)
        healthcare.append(row.healthcare_expenses if row else 0.0)
        other.append(row.other_expenses if row else 0.0)
        real_assets.append(row.real_asset_expenses if row else 0.0)
    return {
        "healthcare": healthcare,
        "other": other,
        "real_assets": real_assets,
    }


def build_chart_payload(plan: Plan, result: SimulationResult, engine_result: EngineResult) -> dict[str, object]:
    years = [row.year for row in result.annual]
    annual_income = [row.income for row in result.annual]
    annual_expenses = [row.expenses for row in result.annual]
    net_worth = [row.net_worth_end for row in result.annual]

    payload: dict[str, object] = {
        "years": years,
        "netWorth": net_worth,
        "income": annual_income,
        "expenses": annual_expenses,
        "expenseBreakdown": _expense_breakdown(engine_result, years),
        "accountsStacked": _stacked_by_account(plan, engine_result, years),
        "accountBalances": _stacked_by_account(plan, engine_result, years),
        "taxBurden": _annual_tax_stacks(engine_result, years),
        "allocation": _allocation_series(plan, engine_result, years),
        "withdrawalSources": _withdrawal_sources(engine_result, years),
        "accountFlowByYear": _account_flow_by_year(plan, engine_result, years),
    }

    if result.net_worth_percentiles:
        payload["success"] = {
            "rate": result.success_rate,
            "p10": [row.p10 for row in result.net_worth_percentiles],
            "p25": [row.p25 for row in result.net_worth_percentiles],
            "p50": [row.p50 for row in result.net_worth_percentiles],
            "p75": [row.p75 for row in result.net_worth_percentiles],
            "p90": [row.p90 for row in result.net_worth_percentiles],
        }
    else:
        payload["success"] = {
            "rate": result.success_rate,
            "p10": [],
            "p25": [],
            "p50": [],
            "p75": [],
            "p90": [],
        }

    return payload
