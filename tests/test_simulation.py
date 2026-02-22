from tests.helpers import clone_plan, write_plan
from tfp.schema import load_plan
from tfp.simulation import run_simulation


def _minimal_mode_plan(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2027-12"
    data["income"] = []
    data["expenses"] = []
    data["contributions"] = []
    data["transfers"] = []
    data["transactions"] = []
    data["real_assets"] = []
    data["social_security"] = []
    data["healthcare"]["pre_medicare"] = []
    data["healthcare"]["post_medicare"] = []
    data["roth_conversions"] = []
    data["rmds"] = {
        "enabled": False,
        "rmd_start_age": 73,
        "accounts": [],
        "destination_account": "Joint Checking",
    }
    data["accounts"] = [
        {
            "name": "Joint Checking",
            "type": "cash",
            "owner": "primary",
            "balance": 100000,
            "cost_basis": None,
            "growth_rate": 0.0,
            "dividend_yield": 0.0,
            "dividend_tax_treatment": "tax_free",
            "reinvest_dividends": False,
            "bond_allocation_percent": 100,
            "yearly_fees": 0.0,
            "allow_withdrawals": True,
        },
        {
            "name": "Portfolio",
            "type": "taxable_brokerage",
            "owner": "primary",
            "balance": 300000,
            "cost_basis": 200000,
            "growth_rate": 0.06,
            "dividend_yield": 0.0,
            "dividend_tax_treatment": "capital_gains",
            "reinvest_dividends": True,
            "bond_allocation_percent": 40,
            "yearly_fees": 0.0,
            "allow_withdrawals": True,
        },
    ]
    data["withdrawal_strategy"] = {
        "order": ["cash", "taxable_brokerage"],
        "account_specific_order": ["Joint Checking", "Portfolio"],
        "use_account_specific": True,
        "rmd_satisfied_first": True,
    }
    path = write_plan(tmp_path, data)
    return load_plan(path)


def test_monte_carlo_uses_seed_and_run_count(tmp_path, sample_plan_dict):
    plan = _minimal_mode_plan(tmp_path, sample_plan_dict)
    plan.simulation_settings.mode = "monte_carlo"
    plan.simulation_settings.monte_carlo.num_simulations = 2

    result_a = run_simulation(plan, seed=123, runs_override=4)
    result_b = run_simulation(plan, seed=123, runs_override=4)

    assert result_a.mode == "monte_carlo"
    assert result_a.scenario_count == 4
    assert result_a.seed == 123
    assert result_a.success_rate is not None
    assert 0.0 <= result_a.success_rate <= 1.0
    assert result_a.net_worth_percentiles is not None
    assert len(result_a.net_worth_percentiles) == len(result_a.annual)
    assert result_a.annual[-1].net_worth_end == result_b.annual[-1].net_worth_end


def test_historical_rolling_periods_produces_multiple_scenarios(tmp_path, sample_plan_dict):
    plan = _minimal_mode_plan(tmp_path, sample_plan_dict)
    plan.simulation_settings.mode = "historical"
    plan.simulation_settings.historical.start_year = 1926
    plan.simulation_settings.historical.end_year = 1930
    plan.simulation_settings.historical.use_rolling_periods = True

    result = run_simulation(plan)

    # 5 historical years with a 2-year plan gives 4 rolling windows.
    assert result.mode == "historical"
    assert result.scenario_count == 4
    assert result.success_rate is not None
    assert result.net_worth_percentiles is not None
    assert len(result.net_worth_percentiles) == len(result.annual)
