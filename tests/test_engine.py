from tests.helpers import clone_plan, write_plan
from tfp.engine import run_deterministic
from tfp.schema import load_plan


def test_deterministic_engine_emits_full_month_range():
    plan = load_plan("sample_plan.json")
    result = run_deterministic(plan)

    assert len(result.monthly) == 480
    assert len(result.annual) == 40
    assert result.annual[0].year == 2026
    assert result.annual[-1].year == 2065


def test_annual_rollup_matches_monthly_totals_for_first_year():
    plan = load_plan("sample_plan.json")
    result = run_deterministic(plan)

    first_year = result.annual[0].year
    months = [m for m in result.monthly if m.year == first_year]
    annual = result.annual[0]

    assert round(sum(m.income for m in months), 6) == round(annual.income, 6)
    assert round(sum(m.tax_withheld for m in months), 6) == round(annual.tax_withheld, 6)
    assert round(sum(m.withdrawals for m in months), 6) == round(annual.withdrawals, 6)


def test_shortfall_triggers_withdrawals(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2026-01"
    data["income"] = []
    data["contributions"] = []
    data["transfers"] = []
    data["transactions"] = []
    data["real_assets"] = []
    data["healthcare"]["pre_medicare"] = []
    data["healthcare"]["post_medicare"] = []
    data["expenses"] = [
        {
            "name": "High expense",
            "owner": "joint",
            "amount": 10000,
            "frequency": "monthly",
            "start_date": "start",
            "end_date": "end",
            "change_over_time": "fixed",
            "change_rate": None,
            "spending_type": "essential",
        }
    ]
    data["accounts"] = [
        {
            "name": "Cash",
            "type": "cash",
            "owner": "primary",
            "balance": 1000,
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
            "name": "Taxable",
            "type": "taxable_brokerage",
            "owner": "primary",
            "balance": 20000,
            "cost_basis": 12000,
            "growth_rate": 0.0,
            "dividend_yield": 0.0,
            "dividend_tax_treatment": "capital_gains",
            "reinvest_dividends": True,
            "bond_allocation_percent": 0,
            "yearly_fees": 0.0,
            "allow_withdrawals": True,
        },
    ]
    data["withdrawal_strategy"] = {
        "order": ["cash", "taxable_brokerage"],
        "account_specific_order": ["Cash", "Taxable"],
        "use_account_specific": True,
        "rmd_satisfied_first": True,
    }
    data["rmds"] = {
        "enabled": False,
        "rmd_start_age": 73,
        "accounts": [],
        "destination_account": "Cash",
    }
    data["roth_conversions"] = []

    path = write_plan(tmp_path, data)
    plan = load_plan(path)
    result = run_deterministic(plan)
    month = result.monthly[0]

    assert month.withdrawals > 0
    assert month.realized_capital_gains > 0


def test_december_tax_settlement_payment_is_recorded(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2026-12"
    data["expenses"] = []
    data["contributions"] = []
    data["transfers"] = []
    data["transactions"] = []
    data["real_assets"] = []
    data["healthcare"]["pre_medicare"] = []
    data["healthcare"]["post_medicare"] = []
    data["income"] = [
        {
            "name": "Salary",
            "owner": "primary",
            "amount": 150000,
            "frequency": "annual",
            "start_date": "start",
            "end_date": "end",
            "change_over_time": "fixed",
            "change_rate": None,
            "tax_handling": "withhold",
            "withhold_percent": 0.05,
        }
    ]
    data["accounts"] = [a for a in data["accounts"] if a["type"] == "cash"]
    data["accounts"][0]["balance"] = 0

    path = write_plan(tmp_path, data)
    plan = load_plan(path)
    result = run_deterministic(plan)

    annual = result.annual[0]
    december = [m for m in result.monthly if m.month == 12][0]
    assert annual.tax_total > annual.tax_withheld
    assert annual.tax_payment > 0
    assert december.tax_settlement > 0


def test_december_tax_refund_is_recorded(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2026-12"
    data["expenses"] = []
    data["contributions"] = []
    data["transfers"] = []
    data["transactions"] = []
    data["real_assets"] = []
    data["healthcare"]["pre_medicare"] = []
    data["healthcare"]["post_medicare"] = []
    data["income"] = [
        {
            "name": "Salary",
            "owner": "primary",
            "amount": 120000,
            "frequency": "annual",
            "start_date": "start",
            "end_date": "end",
            "change_over_time": "fixed",
            "change_rate": None,
            "tax_handling": "withhold",
            "withhold_percent": 0.45,
        }
    ]
    data["accounts"] = [a for a in data["accounts"] if a["type"] == "cash"]
    data["accounts"][0]["balance"] = 0

    path = write_plan(tmp_path, data)
    plan = load_plan(path)
    result = run_deterministic(plan)

    annual = result.annual[0]
    december = [m for m in result.monthly if m.month == 12][0]
    assert annual.tax_refund > 0
    assert annual.tax_payment == 0
    assert december.tax_settlement < 0
