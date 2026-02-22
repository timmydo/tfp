"""Simulation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
import random

from .engine import EngineResult, run_deterministic
from .historical_data import HISTORICAL_ANNUAL_RETURNS
from .schema import Plan


@dataclass(slots=True)
class AnnualSummary:
    year: int
    income: float
    expenses: float
    net_flow: float
    net_worth_end: float


@dataclass(slots=True)
class NetWorthPercentiles:
    year: int
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float


@dataclass(slots=True)
class SimulationResult:
    mode: str
    seed: int | None
    annual: list[AnnualSummary]
    insolvency_years: list[int]
    scenario_count: int = 1
    success_rate: float | None = None
    net_worth_percentiles: list[NetWorthPercentiles] | None = None


def _build_annual_summary(engine_result: EngineResult) -> tuple[list[AnnualSummary], list[int]]:
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


def _plan_years(plan: Plan) -> list[int]:
    start_year = datetime.strptime(plan.plan_settings.plan_start, "%Y-%m").year
    end_year = datetime.strptime(plan.plan_settings.plan_end, "%Y-%m").year
    return list(range(start_year, end_year + 1))


def _aggregate_summaries(
    scenario_annual: list[list[AnnualSummary]],
    scenario_insolvency: list[list[int]],
    mode: str,
    seed: int | None,
) -> SimulationResult:
    scenario_count = len(scenario_annual)
    if scenario_count == 0:
        return SimulationResult(
            mode=mode,
            seed=seed,
            annual=[],
            insolvency_years=[],
            scenario_count=0,
            success_rate=0.0,
            net_worth_percentiles=[],
        )

    def _percentile(values: list[float], pct: float) -> float:
        ordered = sorted(values)
        if not ordered:
            return 0.0
        if len(ordered) == 1:
            return ordered[0]
        position = (len(ordered) - 1) * pct
        low = int(math.floor(position))
        high = int(math.ceil(position))
        if low == high:
            return ordered[low]
        weight = position - low
        return (ordered[low] * (1.0 - weight)) + (ordered[high] * weight)

    years = [row.year for row in scenario_annual[0]]
    aggregated: list[AnnualSummary] = []
    percentiles: list[NetWorthPercentiles] = []
    for idx, year in enumerate(years):
        incomes = [annual[idx].income for annual in scenario_annual]
        expenses = [annual[idx].expenses for annual in scenario_annual]
        net_flows = [annual[idx].net_flow for annual in scenario_annual]
        net_worths = [annual[idx].net_worth_end for annual in scenario_annual]
        aggregated.append(
            AnnualSummary(
                year=year,
                income=sum(incomes) / scenario_count,
                expenses=sum(expenses) / scenario_count,
                net_flow=sum(net_flows) / scenario_count,
                net_worth_end=sum(net_worths) / scenario_count,
            )
        )
        percentiles.append(
            NetWorthPercentiles(
                year=year,
                p10=_percentile(net_worths, 0.10),
                p25=_percentile(net_worths, 0.25),
                p50=_percentile(net_worths, 0.50),
                p75=_percentile(net_worths, 0.75),
                p90=_percentile(net_worths, 0.90),
            )
        )

    insolvency_years = sorted({year for years in scenario_insolvency for year in years})
    success_count = sum(1 for years in scenario_insolvency if not years)
    success_rate = success_count / scenario_count
    return SimulationResult(
        mode=mode,
        seed=seed,
        annual=aggregated,
        insolvency_years=insolvency_years,
        scenario_count=scenario_count,
        success_rate=success_rate,
        net_worth_percentiles=percentiles,
    )


def _clamp_annual_return(value: float) -> float:
    # Prevent invalid monthly geometric conversion for returns <= -100%.
    return max(-0.95, value)


def _monte_carlo_paths(plan: Plan, rng: random.Random) -> list[dict[int, tuple[float, float]]]:
    mc = plan.simulation_settings.monte_carlo
    corr = max(-1.0, min(1.0, mc.correlation))
    corr_scale = math.sqrt(max(0.0, 1.0 - (corr * corr)))
    years = _plan_years(plan)
    paths: list[dict[int, tuple[float, float]]] = []
    for _ in range(max(1, mc.num_simulations)):
        path: dict[int, tuple[float, float]] = {}
        for year in years:
            z1 = rng.gauss(0.0, 1.0)
            z2 = rng.gauss(0.0, 1.0)
            stock = _clamp_annual_return(mc.stock_mean_return + (mc.stock_std_dev * z1))
            bond_shock = (corr * z1) + (corr_scale * z2)
            bond = _clamp_annual_return(mc.bond_mean_return + (mc.bond_std_dev * bond_shock))
            path[year] = (stock, bond)
        paths.append(path)
    return paths


def _historical_paths(plan: Plan) -> list[dict[int, tuple[float, float]]]:
    hist = plan.simulation_settings.historical
    years = _plan_years(plan)
    projection_years = len(years)
    available_years = sorted(
        year
        for year in HISTORICAL_ANNUAL_RETURNS
        if hist.start_year <= year <= hist.end_year
    )
    if not available_years:
        raise ValueError("historical settings produced an empty year range")

    if hist.use_rolling_periods:
        if len(available_years) < projection_years:
            raise ValueError("historical settings do not have enough years for rolling periods")
        starts = range(0, len(available_years) - projection_years + 1)
    else:
        starts = range(1)

    paths: list[dict[int, tuple[float, float]]] = []
    for start_idx in starts:
        path: dict[int, tuple[float, float]] = {}
        for offset, plan_year in enumerate(years):
            hist_idx = start_idx + offset
            if hist_idx >= len(available_years):
                hist_idx = len(available_years) - 1
            hist_year = available_years[hist_idx]
            stock, bond = HISTORICAL_ANNUAL_RETURNS[hist_year]
            path[plan_year] = (_clamp_annual_return(stock), _clamp_annual_return(bond))
        paths.append(path)
    return paths


def run_simulation(plan: Plan, mode_override: str | None = None, runs_override: int | None = None, seed: int | None = None) -> SimulationResult:
    mode = mode_override or plan.simulation_settings.mode

    if mode == "monte_carlo" and runs_override is not None:
        plan.simulation_settings.monte_carlo.num_simulations = runs_override

    if mode == "deterministic":
        annual, insolvency_years = _build_annual_summary(run_deterministic(plan))
        success_rate = 1.0 if not insolvency_years else 0.0
        return SimulationResult(
            mode=mode,
            seed=None,
            annual=annual,
            insolvency_years=insolvency_years,
            scenario_count=1,
            success_rate=success_rate,
            net_worth_percentiles=[],
        )

    if mode == "monte_carlo":
        if seed is None:
            seed = random.randint(1, 2**31 - 1)
        rng = random.Random(seed)
        paths = _monte_carlo_paths(plan, rng)
    elif mode == "historical":
        paths = _historical_paths(plan)
    else:
        raise ValueError(f"unsupported simulation mode: {mode}")

    scenario_annual: list[list[AnnualSummary]] = []
    scenario_insolvency: list[list[int]] = []
    for path in paths:
        engine_result = run_deterministic(plan, annual_return_overrides=path)
        annual, insolvency_years = _build_annual_summary(engine_result)
        scenario_annual.append(annual)
        scenario_insolvency.append(insolvency_years)
    return _aggregate_summaries(scenario_annual, scenario_insolvency, mode=mode, seed=seed)
