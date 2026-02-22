"""Simulation orchestration (initial implementation)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import random

from .schema import Expense, Income, Plan


@dataclass(slots=True)
class AnnualSummary:
    year: int
    income: float
    expenses: float
    net_flow: float
    net_worth_end: float


@dataclass(slots=True)
class SimulationResult:
    mode: str
    seed: int | None
    annual: list[AnnualSummary]
    insolvency_years: list[int]


def _parse_ym(value: str) -> tuple[int, int]:
    dt = datetime.strptime(value, "%Y-%m")
    return dt.year, dt.month


def _active_in_year(start_date: str, end_date: str, year: int, plan_start: str, plan_end: str) -> bool:
    start = plan_start if start_date == "start" else start_date
    end = plan_end if end_date == "end" else end_date
    sy, _ = _parse_ym(start)
    ey, _ = _parse_ym(end)
    return sy <= year <= ey


def _growth_multiplier(change_over_time: str, change_rate: float | None, inflation_rate: float, years_elapsed: int) -> float:
    if years_elapsed <= 0:
        return 1.0
    if change_over_time == "fixed":
        rate = 0.0
    elif change_over_time == "increase":
        rate = change_rate or 0.0
    elif change_over_time == "decrease":
        rate = -(change_rate or 0.0)
    elif change_over_time == "match_inflation":
        rate = inflation_rate
    elif change_over_time == "inflation_plus":
        rate = inflation_rate + (change_rate or 0.0)
    elif change_over_time == "inflation_minus":
        rate = inflation_rate - (change_rate or 0.0)
    else:
        rate = 0.0
    return (1.0 + rate) ** years_elapsed


def _year_amount_income(item: Income, year: int, plan_start: str, plan_end: str, inflation_rate: float) -> float:
    if not _active_in_year(item.start_date, item.end_date, year, plan_start, plan_end):
        return 0.0
    start_year, _ = _parse_ym(plan_start)
    years_elapsed = max(0, year - start_year)
    amount = item.amount * _growth_multiplier(item.change_over_time, item.change_rate, inflation_rate, years_elapsed)
    if item.frequency == "monthly":
        return amount * 12
    if item.frequency == "annual":
        return amount
    if item.frequency == "one_time":
        one_time_year, _ = _parse_ym(item.start_date)
        return amount if one_time_year == year else 0.0
    return 0.0


def _year_amount_expense(item: Expense, year: int, plan_start: str, plan_end: str, inflation_rate: float) -> float:
    if not _active_in_year(item.start_date, item.end_date, year, plan_start, plan_end):
        return 0.0
    start_year, _ = _parse_ym(plan_start)
    years_elapsed = max(0, year - start_year)
    amount = item.amount * _growth_multiplier(item.change_over_time, item.change_rate, inflation_rate, years_elapsed)
    if item.frequency == "monthly":
        return amount * 12
    if item.frequency == "annual":
        return amount
    if item.frequency == "one_time":
        one_time_year, _ = _parse_ym(item.start_date)
        return amount if one_time_year == year else 0.0
    return 0.0


def run_simulation(plan: Plan, mode_override: str | None = None, runs_override: int | None = None, seed: int | None = None) -> SimulationResult:
    mode = mode_override or plan.simulation_settings.mode

    if seed is None and mode in {"monte_carlo", "historical"}:
        seed = random.randint(1, 2**31 - 1)
    if seed is not None:
        random.seed(seed)

    start_year, _ = _parse_ym(plan.plan_settings.plan_start)
    end_year, _ = _parse_ym(plan.plan_settings.plan_end)

    net_worth = sum(a.balance for a in plan.accounts) + sum(r.current_value for r in plan.real_assets)
    annual_rows: list[AnnualSummary] = []
    insolvency_years: list[int] = []

    for year in range(start_year, end_year + 1):
        income = sum(
            _year_amount_income(item, year, plan.plan_settings.plan_start, plan.plan_settings.plan_end, plan.plan_settings.inflation_rate)
            for item in plan.income
        )
        expenses = sum(
            _year_amount_expense(item, year, plan.plan_settings.plan_start, plan.plan_settings.plan_end, plan.plan_settings.inflation_rate)
            for item in plan.expenses
        )
        net_flow = income - expenses
        net_worth += net_flow
        if net_worth < 0:
            insolvency_years.append(year)
        annual_rows.append(AnnualSummary(year=year, income=income, expenses=expenses, net_flow=net_flow, net_worth_end=max(net_worth, 0.0)))

    if mode == "monte_carlo" and runs_override is not None:
        plan.simulation_settings.monte_carlo.num_simulations = runs_override

    return SimulationResult(mode=mode, seed=seed, annual=annual_rows, insolvency_years=insolvency_years)
