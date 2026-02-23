import pytest

from tests.helpers import clone_plan, write_plan
from tfp.schema import load_plan
from tfp.validate import check_plan_sanity, validate_plan


def _run_validation(tmp_path, sample_plan_dict, mutator):
    data = clone_plan(sample_plan_dict)
    mutator(data)
    path = write_plan(tmp_path, data)
    plan = load_plan(path)
    return validate_plan(plan)


def test_sample_plan_validates():
    plan = load_plan("sample_plan.json")
    result = validate_plan(plan)
    assert result.errors == []


@pytest.mark.parametrize(
    ("mutator", "expected_error"),
    [
        (
            lambda d: d.update({"accounts": [a for a in d["accounts"] if a["type"] != "cash"]}),
            "accounts: at least one cash account is required",
        ),
        (
            lambda d: d["accounts"][1].update({"cost_basis": None}),
            "accounts[1].cost_basis: required for taxable_brokerage accounts",
        ),
        (
            lambda d: d["transfers"][0].update({"start_date": "2039-01", "end_date": "2038-12"}),
            "transfers[0].start_date/transfers[0].end_date: start_date must be <= end_date",
        ),
        (
            lambda d: d["income"][0].update({"withhold_percent": None}),
            "income[0].withhold_percent: required when tax_handling is 'withhold'",
        ),
        (
            lambda d: d["expenses"][0].update({"change_over_time": "increase", "change_rate": None}),
            "expenses[0].change_rate: required when change_over_time is 'increase'",
        ),
        (
            lambda d: d["rmds"].update({"accounts": ["Alex Roth IRA"]}),
            "rmds.accounts[0]: account must be 401k or traditional_ira",
        ),
        (
            lambda d: d["roth_conversions"][0].update({"from_account": "Vanguard Taxable"}),
            "roth_conversions[0].from_account: must be traditional_ira or 401k",
        ),
        (
            lambda d: d["income"][0].update({"withhold_percent": 1.5}),
            "income[0].withhold_percent: must be <= 1",
        ),
        (
            lambda d: d["accounts"][0].update({"bond_allocation_percent": 150}),
            "accounts[0].bond_allocation_percent: must be <= 100",
        ),
        (
            lambda d: d["simulation_settings"]["monte_carlo"].update({"correlation": 1.5}),
            "simulation_settings.monte_carlo.correlation: must be <= 1",
        ),
        (
            lambda d: d["social_security"][0].update({"fra_age_months": 12}),
            "social_security[0].fra_age_months: must be <= 11",
        ),
        (
            lambda d: d["healthcare"]["irmaa"].update({"lookback_years": 0}),
            "healthcare.irmaa.lookback_years: must be >= 1",
        ),
    ],
)
def test_validation_error_cases(tmp_path, sample_plan_dict, mutator, expected_error):
    result = _run_validation(tmp_path, sample_plan_dict, mutator)
    assert expected_error in result.errors


def test_invalid_owner_path_context(tmp_path, sample_plan_dict):
    def mutator(data):
        data["income"][0]["owner"] = "partner"

    result = _run_validation(tmp_path, sample_plan_dict, mutator)
    assert any(err.startswith("income[0].owner:") for err in result.errors)


def test_single_with_spouse_emits_warning(tmp_path, sample_plan_dict):
    def mutator(data):
        data["filing_status"] = "single"

    result = _run_validation(tmp_path, sample_plan_dict, mutator)
    assert result.errors == []
    assert any("filing_status: 'single' with people.spouse present is unusual but allowed" in w for w in result.warnings)


def test_mfj_requires_spouse(tmp_path, sample_plan_dict):
    def mutator(data):
        del data["people"]["spouse"]
        data["accounts"] = [a for a in data["accounts"] if a["owner"] != "spouse"]
        data["income"] = [i for i in data["income"] if i["owner"] != "spouse"]
        data["social_security"] = [s for s in data["social_security"] if s["owner"] != "spouse"]
        data["healthcare"]["pre_medicare"] = [h for h in data["healthcare"]["pre_medicare"] if h["owner"] != "spouse"]
        data["healthcare"]["post_medicare"] = [h for h in data["healthcare"]["post_medicare"] if h["owner"] != "spouse"]
        data["accounts"] = [a for a in data["accounts"] if a["name"] != "Jamie Traditional IRA"]
        data["withdrawal_strategy"]["account_specific_order"] = [
            n for n in data["withdrawal_strategy"]["account_specific_order"] if n != "Jamie Traditional IRA"
        ]
        data["rmds"]["accounts"] = [a for a in data["rmds"]["accounts"] if a != "Jamie Traditional IRA"]
        data["roth_conversions"] = []

    result = _run_validation(tmp_path, sample_plan_dict, mutator)
    assert "filing_status: 'married_filing_jointly' requires people.spouse" in result.errors


def test_duplicate_names_are_rejected(tmp_path, sample_plan_dict):
    def mutator(data):
        dup = clone_plan(data["accounts"][0])
        data["accounts"].append(dup)
        data["real_assets"][1]["name"] = "Primary Home"

    result = _run_validation(tmp_path, sample_plan_dict, mutator)
    assert "accounts[6].name: duplicate account name 'Joint Checking'" in result.errors
    assert "real_assets[1].name: duplicate real asset name 'Primary Home'" in result.errors


def test_sell_asset_purchase_price_error_points_to_asset_index(tmp_path, sample_plan_dict):
    def mutator(data):
        data["real_assets"][1]["purchase_price"] = None

    result = _run_validation(tmp_path, sample_plan_dict, mutator)
    assert "real_assets[1].purchase_price: required for assets referenced by sell_asset transactions" in result.errors


def test_roth_conversion_requires_exactly_one_amount_mode(tmp_path, sample_plan_dict):
    def mutator(data):
        data["roth_conversions"][0]["annual_amount"] = None
        data["roth_conversions"][0]["fill_to_bracket"] = None

    result = _run_validation(tmp_path, sample_plan_dict, mutator)
    assert "roth_conversions[0]: provide exactly one of annual_amount or fill_to_bracket" in result.errors


def test_sanity_checks_warn_for_unusual_assumptions(tmp_path, sample_plan_dict):
    def mutator(data):
        data["plan_settings"]["inflation_rate"] = 0.09
        data["accounts"][0]["growth_rate"] = 0.20
        data["accounts"][0]["dividend_yield"] = 0.07
        data["accounts"][0]["yearly_fees"] = 0.03
        data["simulation_settings"]["monte_carlo"]["num_simulations"] = 100
        data["simulation_settings"]["monte_carlo"]["stock_mean_return"] = 0.16

    data = clone_plan(sample_plan_dict)
    mutator(data)
    path = write_plan(tmp_path, data)
    plan = load_plan(path)
    result = check_plan_sanity(plan)

    assert any("plan_settings.inflation_rate" in msg for msg in result.warnings)
    assert any("accounts[0]" in msg and ".growth_rate" in msg for msg in result.warnings)
    assert any("accounts[0]" in msg and ".yearly_fees" in msg for msg in result.warnings)
    assert any("simulation_settings.monte_carlo.num_simulations" in msg for msg in result.warnings)
    assert any("simulation_settings.monte_carlo.stock_mean_return" in msg for msg in result.warnings)
