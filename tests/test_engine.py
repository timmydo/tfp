from tests.helpers import clone_plan, write_plan
from tfp.engine import run_deterministic
from tfp.real_assets import change_rate_for_year
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


def test_employer_match_uses_annual_salary_cap_for_lump_sum_contribution(tmp_path, sample_plan_dict):
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
    data["contributions"] = [
        {
            "name": "Frontloaded 401k",
            "source_account": "income",
            "destination_account": "401k",
            "amount": 7200,
            "frequency": "annual",
            "start_date": "start",
            "end_date": "end",
            "change_over_time": "fixed",
            "change_rate": None,
            "employer_match": {
                "match_percent": 0.5,
                "up_to_percent_of_salary": 0.06,
                "salary_reference": "Salary",
            },
        }
    ]
    data["expenses"] = []
    data["transfers"] = []
    data["transactions"] = []
    data["real_assets"] = []
    data["healthcare"]["pre_medicare"] = []
    data["healthcare"]["post_medicare"] = []
    data["social_security"] = []
    data["accounts"] = [
        {
            "name": "Cash",
            "type": "cash",
            "owner": "primary",
            "balance": 0,
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
            "name": "401k",
            "type": "401k",
            "owner": "primary",
            "balance": 0,
            "cost_basis": None,
            "growth_rate": 0.0,
            "dividend_yield": 0.0,
            "dividend_tax_treatment": "tax_free",
            "reinvest_dividends": True,
            "bond_allocation_percent": 0,
            "yearly_fees": 0.0,
            "allow_withdrawals": True,
        },
    ]
    data["withdrawal_strategy"] = {
        "order": ["cash", "401k"],
        "account_specific_order": ["Cash", "401k"],
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

    january = result.monthly[0]
    annual_401k = result.account_annual["401k"][0]

    assert january.account_flow_reasons["401k"]["Contribution in: Frontloaded 401k"] == 7200.0
    assert january.account_flow_reasons["401k"]["Employer match: Frontloaded 401k"] == 3600.0
    assert annual_401k.contributions == 10800.0


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


def test_buy_asset_creates_real_asset_state_when_transaction_executes(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2026-03"
    data["income"] = []
    data["expenses"] = []
    data["contributions"] = []
    data["transfers"] = []
    data["social_security"] = []
    data["healthcare"]["pre_medicare"] = []
    data["healthcare"]["post_medicare"] = []
    data["roth_conversions"] = []
    data["rmds"] = {
        "enabled": False,
        "rmd_start_age": 73,
        "accounts": [],
        "destination_account": "Cash",
    }
    data["accounts"] = [
        {
            "name": "Cash",
            "type": "cash",
            "owner": "primary",
            "balance": 300000,
            "cost_basis": None,
            "growth_rate": 0.0,
            "dividend_yield": 0.0,
            "dividend_tax_treatment": "tax_free",
            "reinvest_dividends": False,
            "bond_allocation_percent": 100,
            "yearly_fees": 0.0,
            "allow_withdrawals": True,
        }
    ]
    data["real_assets"] = [
        {
            "name": "Future Home",
            "current_value": 999999,
            "purchase_price": None,
            "primary_residence": True,
            "change_over_time": "fixed",
            "change_rate": None,
            "property_tax_rate": 0.012,
            "mortgage": None,
            "maintenance_expenses": [
                {
                    "name": "Upkeep",
                    "amount": 100,
                    "frequency": "monthly",
                }
            ],
        }
    ]
    data["transactions"] = [
        {
            "name": "Buy future home",
            "date": "2026-02",
            "type": "buy_asset",
            "amount": 250000,
            "fees": 10000,
            "tax_treatment": "tax_free",
            "linked_asset": "Future Home",
            "deposit_to_account": None,
        }
    ]

    path = write_plan(tmp_path, data)
    plan = load_plan(path)
    result = run_deterministic(plan)

    january, february, march = result.monthly

    assert round(january.net_worth_end, 2) == 300000.00
    assert round(january.real_asset_expenses, 2) == 0.00

    assert round(february.net_worth_end, 2) == 290000.00
    assert round(february.real_asset_expenses, 2) == 0.00

    assert round(march.real_asset_expenses, 2) == 350.00
    assert round(march.net_worth_end, 2) == 289650.00


def test_transfer_with_insufficient_source_balance_does_not_record_impossible_withdrawal(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2026-01"
    data["income"] = []
    data["expenses"] = []
    data["contributions"] = []
    data["transactions"] = []
    data["real_assets"] = []
    data["healthcare"]["pre_medicare"] = []
    data["healthcare"]["post_medicare"] = []
    data["social_security"] = []
    data["roth_conversions"] = []
    data["rmds"] = {
        "enabled": False,
        "rmd_start_age": 73,
        "accounts": [],
        "destination_account": "Cash",
    }
    data["accounts"] = [
        {
            "name": "Cash",
            "type": "cash",
            "owner": "primary",
            "balance": 0,
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
            "name": "Traditional IRA",
            "type": "traditional_ira",
            "owner": "primary",
            "balance": 0,
            "cost_basis": None,
            "growth_rate": 0.0,
            "dividend_yield": 0.0,
            "dividend_tax_treatment": "tax_free",
            "reinvest_dividends": True,
            "bond_allocation_percent": 40,
            "yearly_fees": 0.0,
            "allow_withdrawals": True,
        },
    ]
    data["transfers"] = [
        {
            "name": "Impossible transfer",
            "from_account": "Traditional IRA",
            "to_account": "Cash",
            "amount": 80000,
            "frequency": "one_time",
            "start_date": "2026-01",
            "end_date": "2026-01",
            "tax_treatment": "income",
        }
    ]
    data["withdrawal_strategy"] = {
        "order": ["cash", "traditional_ira"],
        "account_specific_order": ["Cash", "Traditional IRA"],
        "use_account_specific": True,
        "rmd_satisfied_first": True,
    }

    path = write_plan(tmp_path, data)
    plan = load_plan(path)
    result = run_deterministic(plan)

    ira_annual = result.account_annual["Traditional IRA"][0]
    month = result.monthly[0]
    assert ira_annual.withdrawals == 0
    assert month.transfers == 0


def test_change_rate_for_year_handles_decrease():
    assert change_rate_for_year("decrease", 0.05, 0.03) == -0.05
    assert change_rate_for_year("decrease", None, 0.03) == 0.0


def test_investment_income_feeds_niit(tmp_path, sample_plan_dict):
    """Dividends taxed as 'income' should appear in investment_income and affect NIIT."""
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2026-12"
    data["income"] = [
        {
            "name": "Salary",
            "owner": "primary",
            "amount": 300000,
            "frequency": "annual",
            "start_date": "start",
            "end_date": "end",
            "change_over_time": "fixed",
            "change_rate": None,
            "tax_handling": "withhold",
            "withhold_percent": 0.25,
        }
    ]
    data["expenses"] = []
    data["contributions"] = []
    data["transfers"] = []
    data["transactions"] = []
    data["real_assets"] = []
    data["healthcare"]["pre_medicare"] = []
    data["healthcare"]["post_medicare"] = []
    data["roth_conversions"] = []
    data["social_security"] = []
    data["accounts"] = [
        {
            "name": "Cash",
            "type": "cash",
            "owner": "primary",
            "balance": 50000,
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
            "balance": 500000,
            "cost_basis": 500000,
            "growth_rate": 0.0,
            "dividend_yield": 0.06,
            "dividend_tax_treatment": "income",
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
    data["tax_settings"]["niit_enabled"] = True

    path = write_plan(tmp_path, data)
    plan = load_plan(path)
    result = run_deterministic(plan)

    annual = result.annual[0]
    assert annual.investment_income > 0
    assert annual.tax_niit > 0


def test_transfer_capital_gains_non_brokerage(tmp_path, sample_plan_dict):
    """Transfer with tax_treatment 'capital_gains' from non-brokerage should record gains."""
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2026-12"
    data["income"] = []
    data["expenses"] = []
    data["contributions"] = []
    data["transactions"] = []
    data["real_assets"] = []
    data["healthcare"]["pre_medicare"] = []
    data["healthcare"]["post_medicare"] = []
    data["roth_conversions"] = []
    data["social_security"] = []
    data["accounts"] = [
        {
            "name": "Cash",
            "type": "cash",
            "owner": "primary",
            "balance": 0,
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
            "name": "Other Account",
            "type": "other",
            "owner": "primary",
            "balance": 100000,
            "cost_basis": None,
            "growth_rate": 0.0,
            "dividend_yield": 0.0,
            "dividend_tax_treatment": "tax_free",
            "reinvest_dividends": False,
            "bond_allocation_percent": 0,
            "yearly_fees": 0.0,
            "allow_withdrawals": True,
        },
    ]
    data["transfers"] = [
        {
            "name": "CG transfer",
            "from_account": "Other Account",
            "to_account": "Cash",
            "amount": 50000,
            "frequency": "one_time",
            "start_date": "2026-01",
            "end_date": "2026-01",
            "tax_treatment": "capital_gains",
        }
    ]
    data["withdrawal_strategy"] = {
        "order": ["cash", "other"],
        "account_specific_order": ["Cash", "Other Account"],
        "use_account_specific": True,
        "rmd_satisfied_first": True,
    }
    data["rmds"] = {
        "enabled": False,
        "rmd_start_age": 73,
        "accounts": [],
        "destination_account": "Cash",
    }

    path = write_plan(tmp_path, data)
    plan = load_plan(path)
    result = run_deterministic(plan)

    annual = result.annual[0]
    assert annual.realized_capital_gains >= 50000
