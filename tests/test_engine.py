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


def test_annual_income_is_distributed_monthly(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2026-12"
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
            "tax_handling": "tax_exempt",
            "withhold_percent": None,
        }
    ]
    data["social_security"] = []
    data["expenses"] = []
    data["contributions"] = []
    data["transfers"] = []
    data["transactions"] = []
    data["real_assets"] = []
    data["healthcare"]["pre_medicare"] = []
    data["healthcare"]["post_medicare"] = []
    data["accounts"] = [a for a in data["accounts"] if a["type"] == "cash"]
    data["accounts"][0]["balance"] = 0

    path = write_plan(tmp_path, data)
    plan = load_plan(path)
    result = run_deterministic(plan)

    assert len(result.monthly) == 12
    assert all(round(month.income, 2) == 10000.00 for month in result.monthly)
    assert round(result.annual[0].income, 2) == 120000.00


def test_one_time_income_remains_lump_sum(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2026-12"
    data["income"] = [
        {
            "name": "Bonus",
            "owner": "primary",
            "amount": 120000,
            "frequency": "one_time",
            "start_date": "2026-03",
            "end_date": "2026-03",
            "change_over_time": "fixed",
            "change_rate": None,
            "tax_handling": "tax_exempt",
            "withhold_percent": None,
        }
    ]
    data["social_security"] = []
    data["expenses"] = []
    data["contributions"] = []
    data["transfers"] = []
    data["transactions"] = []
    data["real_assets"] = []
    data["healthcare"]["pre_medicare"] = []
    data["healthcare"]["post_medicare"] = []
    data["accounts"] = [a for a in data["accounts"] if a["type"] == "cash"]
    data["accounts"][0]["balance"] = 0

    path = write_plan(tmp_path, data)
    plan = load_plan(path)
    result = run_deterministic(plan)

    income_by_month = {month.month: round(month.income, 2) for month in result.monthly}
    assert income_by_month[3] == 120000.00
    assert sum(amount for month, amount in income_by_month.items() if month != 3) == 0.00


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


def test_monthly_estimated_tax_payments_reduce_december_settlement(tmp_path, sample_plan_dict):
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
    assert annual.tax_estimated_payments > 0
    assert any(m.tax_estimated_payment > 0 for m in result.monthly)
    assert december.tax_settlement >= 0


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
    assert annual.tax_estimated_payments == 0
    assert december.tax_settlement < 0


def test_primary_residence_sale_applies_gain_exclusion(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2031-06"
    data["plan_settings"]["plan_end"] = "2031-06"
    data["income"] = []
    data["expenses"] = []
    data["contributions"] = []
    data["transfers"] = []
    data["healthcare"]["pre_medicare"] = []
    data["healthcare"]["post_medicare"] = []
    data["accounts"] = [a for a in data["accounts"] if a["type"] == "cash"]
    data["accounts"][0]["balance"] = 0
    data["real_assets"] = [
        {
            "name": "Primary Home",
            "current_value": 1_200_000,
            "purchase_price": 300_000,
            "primary_residence": True,
            "change_over_time": "fixed",
            "change_rate": None,
            "property_tax_rate": 0.0,
            "mortgage": None,
            "maintenance_expenses": [],
        }
    ]
    data["transactions"] = [
        {
            "name": "Sell home",
            "date": "2031-06",
            "type": "sell_asset",
            "amount": 1_100_000,
            "fees": 0,
            "tax_treatment": "capital_gains",
            "linked_asset": "Primary Home",
            "deposit_to_account": "Joint Checking",
        }
    ]
    data["rmds"]["enabled"] = False
    data["roth_conversions"] = []

    path = write_plan(tmp_path, data)
    plan = load_plan(path)
    result = run_deterministic(plan)

    month = result.monthly[0]
    # MFJ exclusion is 500k: gain = 1.1m - 300k - 500k = 300k
    assert round(month.realized_capital_gains, 2) == 300000.00
