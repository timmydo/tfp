from tests.helpers import clone_plan, write_plan
from tfp.engine import run_deterministic
from tfp.schema import load_plan
from tfp.tax import YearIncomeSummary, compute_total_tax


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
