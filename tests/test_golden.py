from tests.helpers import clone_plan, write_plan
from tfp.engine import run_deterministic
from tfp.schema import (
    HealthcarePostMedicare,
    HealthcarePreMedicare,
    Mortgage,
    RealAsset,
    SocialSecurity,
    load_plan,
)
from tfp.simulation import run_simulation


def _minimal_single_person_plan(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["people"]["primary"]["state"] = "CA"
    data["people"].pop("spouse", None)
    data["filing_status"] = "single"
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2026-12"
    data["income"] = []
    data["expenses"] = []
    data["contributions"] = []
    data["transfers"] = []
    data["transactions"] = []
    data["real_assets"] = []
    data["social_security"] = []
    data["healthcare"]["pre_medicare"] = []
    data["healthcare"]["post_medicare"] = []
    data["accounts"] = [
        {
            "name": "Cash",
            "type": "cash",
            "owner": "primary",
            "balance": 10000,
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
            "name": "IRA",
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
        "account_specific_order": ["Cash", "IRA"],
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
    return load_plan(path)


def test_sample_plan_deterministic_golden_metrics():
    plan = load_plan("sample_plan.json")
    result = run_simulation(plan, mode_override="deterministic")

    assert len(result.annual) == 40
    assert result.annual[0].year == 2026
    assert result.annual[-1].year == 2065

    first = result.annual[0]
    tenth = result.annual[9]
    last = result.annual[-1]

    assert round(first.income) == 300000
    assert round(first.expenses) == 212169
    assert round(first.net_worth_end) == 2497260

    assert tenth.year == 2035
    assert round(tenth.net_worth_end) == 4130905

    assert round(last.income) == 118257
    assert round(last.expenses) == 531417
    assert round(last.net_worth_end) == 2935834

    assert result.insolvency_years == [2061, 2062, 2063, 2064, 2065]


def test_social_security_starts_in_claiming_month(tmp_path, sample_plan_dict):
    plan = _minimal_single_person_plan(tmp_path, sample_plan_dict)
    plan.people.primary.birthday = "1961-06"
    plan.social_security = [
        SocialSecurity(
            owner="primary",
            pia_at_fra=2400,
            fra_age_years=67,
            fra_age_months=0,
            claiming_age_years=65,
            claiming_age_months=0,
            cola_assumption="fixed",
            cola_rate=0.0,
        )
    ]

    result = run_deterministic(plan)
    monthly = {(m.year, m.month): m.income for m in result.monthly}

    assert monthly[(2026, 5)] == 0.0
    assert monthly[(2026, 6)] > 0.0


def test_medicare_transition_switches_cost_model_in_birthday_month(tmp_path, sample_plan_dict):
    plan = _minimal_single_person_plan(tmp_path, sample_plan_dict)
    plan.people.primary.birthday = "1961-06"
    plan.healthcare.pre_medicare = [
        HealthcarePreMedicare(
            owner="primary",
            monthly_premium=1200,
            annual_out_of_pocket=0,
            start_date="start",
            end_date=None,
            change_over_time="fixed",
            change_rate=None,
        )
    ]
    plan.healthcare.post_medicare = [
        HealthcarePostMedicare(
            owner="primary",
            medicare_start_date=None,
            part_b_monthly_premium=100,
            supplement_monthly_premium=50,
            part_d_monthly_premium=25,
            annual_out_of_pocket=0,
            change_over_time="fixed",
            change_rate=None,
        )
    ]

    result = run_deterministic(plan)
    monthly = {(m.year, m.month): m.healthcare_expenses for m in result.monthly}

    assert round(monthly[(2026, 5)], 2) == 1200.00
    assert round(monthly[(2026, 6)], 2) == 175.00


def test_rmd_starts_in_first_required_year(tmp_path, sample_plan_dict):
    plan = _minimal_single_person_plan(tmp_path, sample_plan_dict)
    plan.plan_settings.plan_start = "2026-12"
    plan.plan_settings.plan_end = "2026-12"
    plan.people.primary.birthday = "1953-01"
    plan.rmds.enabled = True
    plan.rmds.accounts = ["IRA"]
    plan.rmds.destination_account = "Cash"

    result = run_deterministic(plan)
    assert result.annual[0].withdrawals > 0

    plan.plan_settings.plan_start = "2025-12"
    plan.plan_settings.plan_end = "2025-12"
    result_before = run_deterministic(plan)
    assert result_before.annual[0].withdrawals == 0


def test_mortgage_payoff_month_stops_future_payments(tmp_path, sample_plan_dict):
    plan = _minimal_single_person_plan(tmp_path, sample_plan_dict)
    plan.plan_settings.plan_start = "2026-01"
    plan.plan_settings.plan_end = "2026-04"
    plan.real_assets = [
        RealAsset(
            name="Test Home",
            current_value=100000,
            purchase_price=100000,
            primary_residence=True,
            change_over_time="fixed",
            change_rate=None,
            property_tax_rate=0.0,
            mortgage=Mortgage(
                payment=600,
                remaining_balance=1000,
                interest_rate=0.0,
                end_date="2030-01",
            ),
            maintenance_expenses=[],
        )
    ]

    result = run_deterministic(plan)
    expenses = [m.real_asset_expenses for m in result.monthly]

    assert [round(v, 2) for v in expenses] == [600.0, 400.0, 0.0, 0.0]
