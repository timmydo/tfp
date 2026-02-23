from tests.helpers import clone_plan, write_plan
from tfp.engine import run_deterministic
from tfp.schema import load_plan
from tfp.tax import YearIncomeSummary, compute_fica, compute_total_tax


def test_early_withdrawal_penalty_flows_into_annual_tax(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-12"
    data["plan_settings"]["plan_end"] = "2026-12"
    data["people"]["primary"]["birthday"] = "1980-01"
    data["people"]["spouse"]["birthday"] = "1983-09"

    data["income"] = []
    data["contributions"] = []
    data["transfers"] = []
    data["transactions"] = []
    data["real_assets"] = []
    data["healthcare"]["pre_medicare"] = []
    data["healthcare"]["post_medicare"] = []
    data["social_security"] = []
    data["rmds"] = {
        "enabled": False,
        "rmd_start_age": 73,
        "accounts": [],
        "destination_account": "Cash",
    }
    data["roth_conversions"] = []

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
            "name": "Trad IRA",
            "type": "traditional_ira",
            "owner": "primary",
            "balance": 100000,
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
        "order": ["cash", "traditional_ira"],
        "account_specific_order": ["Cash", "Trad IRA"],
        "use_account_specific": True,
        "rmd_satisfied_first": True,
    }
    data["expenses"] = [
        {
            "name": "Large bill",
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

    path = write_plan(tmp_path, data)
    plan = load_plan(path)
    result = run_deterministic(plan)

    annual = result.annual[0]
    assert annual.withdrawals > 0
    assert annual.tax_penalties > 0

def test_tax_settlement_recomputes_after_shortfall_withdrawals(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-12"
    data["plan_settings"]["plan_end"] = "2026-12"
    data["people"]["primary"]["birthday"] = "1970-01"
    data["people"]["spouse"]["birthday"] = "1970-01"

    data["contributions"] = []
    data["transfers"] = []
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
    data["tax_settings"]["itemized_deductions"] = {
        "salt_cap": 0,
        "mortgage_interest_deductible": False,
        "charitable_contributions": 0,
    }

    data["income"] = [
        {
            "name": "Salary",
            "owner": "primary",
            "amount": 60000,
            "frequency": "annual",
            "start_date": "start",
            "end_date": "end",
            "change_over_time": "fixed",
            "change_rate": None,
            "tax_handling": "withhold",
            "withhold_percent": 0.0,
        }
    ]
    data["expenses"] = [
        {
            "name": "Consume cash",
            "owner": "joint",
            "amount": 60000,
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
            "name": "Trad IRA",
            "type": "traditional_ira",
            "owner": "primary",
            "balance": 100000,
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
        "order": ["cash", "traditional_ira"],
        "account_specific_order": ["Cash", "Trad IRA"],
        "use_account_specific": True,
        "rmd_satisfied_first": True,
    }

    path = write_plan(tmp_path, data)
    plan = load_plan(path)
    result = run_deterministic(plan)

    annual = result.annual[0]
    baseline_tax = compute_total_tax(
        YearIncomeSummary(
            year=2026,
            filing_status=plan.filing_status,
            state=plan.people.primary.state or "CA",
            ordinary_income=60000,
            capital_gains=0.0,
            qualified_dividends=0.0,
            itemized_deductions=0.0,
            early_withdrawal_penalty=0.0,
        ),
        plan.tax_settings,
        inflation_rate=plan.plan_settings.inflation_rate,
    ).total_tax
    assert annual.taxable_ordinary_income > 60000
    # Extra settlement-funded IRA withdrawals should feed back into final tax.
    assert annual.tax_total > baseline_tax


def test_itemized_mortgage_interest_uses_actual_interest_not_proxy(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-12"
    data["plan_settings"]["plan_end"] = "2026-12"
    data["contributions"] = []
    data["transfers"] = []
    data["transactions"] = []
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
    data["tax_settings"]["itemized_deductions"] = {
        "salt_cap": 0,
        "mortgage_interest_deductible": True,
        "charitable_contributions": 0,
    }
    data["income"] = [
        {
            "name": "Salary",
            "owner": "primary",
            "amount": 200000,
            "frequency": "annual",
            "start_date": "start",
            "end_date": "end",
            "change_over_time": "fixed",
            "change_rate": None,
            "tax_handling": "withhold",
            "withhold_percent": 0.0,
        }
    ]
    data["accounts"] = [
        {
            "name": "Cash",
            "type": "cash",
            "owner": "primary",
            "balance": 1000000,
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
            "name": "No Mortgage Asset",
            "current_value": 1_000_000,
            "purchase_price": 1_000_000,
            "primary_residence": False,
            "change_over_time": "fixed",
            "change_rate": None,
            "property_tax_rate": 0.012,
            "mortgage": None,
            "maintenance_expenses": [
                {"name": "Monthly upkeep", "amount": 10_000, "frequency": "monthly"},
            ],
        }
    ]
    data["expenses"] = []

    path = write_plan(tmp_path, data)
    plan = load_plan(path)
    result = run_deterministic(plan)

    annual = result.annual[0]
    assert annual.real_asset_expenses > 0
    assert annual.mortgage_interest_paid == 0

    expected = compute_total_tax(
        YearIncomeSummary(
            year=2026,
            filing_status=plan.filing_status,
            state=plan.people.primary.state or "CA",
            ordinary_income=annual.taxable_ordinary_income,
            capital_gains=annual.realized_capital_gains,
            qualified_dividends=annual.qualified_dividends,
            itemized_deductions=0.0,
            early_withdrawal_penalty=annual.tax_penalties,
        ),
        plan.tax_settings,
        inflation_rate=plan.plan_settings.inflation_rate,
    )
    assert round(annual.tax_total, 2) == round(expected.total_tax + annual.tax_withheld, 2)


def test_fica_withholding_is_applied_and_counted_in_total_tax(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-12"
    data["plan_settings"]["plan_end"] = "2026-12"
    data["contributions"] = []
    data["transfers"] = []
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
    data["income"] = [
        {
            "name": "Salary",
            "owner": "primary",
            "amount": 100000,
            "frequency": "annual",
            "start_date": "start",
            "end_date": "end",
            "change_over_time": "fixed",
            "change_rate": None,
            "tax_handling": "withhold",
            "withhold_percent": 0.0,
        }
    ]
    data["expenses"] = []
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
        }
    ]
    path = write_plan(tmp_path, data)
    plan = load_plan(path)
    result = run_deterministic(plan)

    annual = result.annual[0]
    expected_fica = compute_fica(100000, 0, 2026, filing_status=plan.filing_status)
    expected_income_tax = compute_total_tax(
        YearIncomeSummary(
            year=2026,
            filing_status=plan.filing_status,
            state=plan.people.primary.state or "CA",
            ordinary_income=annual.taxable_ordinary_income,
            capital_gains=annual.realized_capital_gains,
            qualified_dividends=annual.qualified_dividends,
            itemized_deductions=0.0,
            early_withdrawal_penalty=annual.tax_penalties,
        ),
        plan.tax_settings,
        inflation_rate=plan.plan_settings.inflation_rate,
    )
    assert round(annual.tax_withheld, 2) == round(expected_fica, 2)
    assert round(annual.tax_total - expected_income_tax.total_tax, 2) == round(expected_fica, 2)


def test_roth_early_withdrawal_penalty_applies_to_earnings_only(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2026-12"
    data["people"]["primary"]["birthday"] = "1980-01"
    data["people"]["spouse"]["birthday"] = "1980-01"
    data["income"] = []
    data["contributions"] = []
    data["transfers"] = []
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
            "name": "Roth IRA",
            "type": "roth_ira",
            "owner": "primary",
            "balance": 10000,
            "cost_basis": None,
            "growth_rate": 1.0,
            "dividend_yield": 0.0,
            "dividend_tax_treatment": "tax_free",
            "reinvest_dividends": True,
            "bond_allocation_percent": 0,
            "yearly_fees": 0.0,
            "allow_withdrawals": True,
        },
    ]
    data["withdrawal_strategy"] = {
        "order": ["cash", "roth_ira"],
        "account_specific_order": ["Cash", "Roth IRA"],
        "use_account_specific": True,
        "rmd_satisfied_first": True,
    }
    data["expenses"] = [
        {
            "name": "Spend",
            "owner": "joint",
            "amount": 5300,
            "frequency": "monthly",
            "start_date": "start",
            "end_date": "end",
            "change_over_time": "fixed",
            "change_rate": None,
            "spending_type": "essential",
        }
    ]

    path = write_plan(tmp_path, data)
    plan = load_plan(path)
    result = run_deterministic(plan)

    annual = result.annual[0]
    assert annual.withdrawals > 10000
    assert annual.tax_penalties > 0
