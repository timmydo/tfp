"""Simulation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
import random
import warnings

from .engine import run_deterministic
from .schema import Plan


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


def _build_annual_summary(plan: Plan) -> tuple[list[AnnualSummary], list[int]]:
    engine_result = run_deterministic(plan)
    annual: list[AnnualSummary] = []
    for row in engine_result.annual:
        expenses = row.healthcare_expenses + row.other_expenses + row.real_asset_expenses
        taxes = row.tax_total if row.tax_total > 0 else row.tax_withheld
        net_flow = row.income - expenses - taxes
        annual.append(
            AnnualSummary(
                year=row.year,
                income=row.income,
                expenses=expenses,
                net_flow=net_flow,
                net_worth_end=row.net_worth_end,
            )
        )
    return annual, engine_result.insolvency_years


def run_simulation(plan: Plan, mode_override: str | None = None, runs_override: int | None = None, seed: int | None = None) -> SimulationResult:
    mode = mode_override or plan.simulation_settings.mode

    if mode == "monte_carlo" and runs_override is not None:
        plan.simulation_settings.monte_carlo.num_simulations = runs_override

    if mode in {"monte_carlo", "historical"}:
        if seed is None:
            seed = random.randint(1, 2**31 - 1)
        random.seed(seed)
        warnings.warn(
            f"{mode} currently falls back to deterministic engine output",
            RuntimeWarning,
            stacklevel=2,
        )

    annual, insolvency_years = _build_annual_summary(plan)
    return SimulationResult(mode=mode, seed=seed, annual=annual, insolvency_years=insolvency_years)
