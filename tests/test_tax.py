import pytest

from tfp.schema import ItemizedDeductions, TaxSettings
from tfp.tax_data import CAPITAL_GAINS_BRACKETS, FEDERAL_BRACKETS, FICA_RATES, STANDARD_DEDUCTIONS
from tfp.tax import (
    YearIncomeSummary,
    compute_fica,
    compute_capital_gains_tax,
    compute_federal_income_tax,
    compute_state_tax,
    compute_total_tax,
)


def _default_tax_settings() -> TaxSettings:
    return TaxSettings(
        use_current_brackets=True,
        bracket_year=2026,
        federal_effective_rate_override=None,
        state_effective_rate_override=None,
        capital_gains_rate_override=None,
        standard_deduction_override=None,
        itemized_deductions=ItemizedDeductions(
            salt_cap=10000,
            mortgage_interest_deductible=True,
            charitable_contributions=0,
        ),
        niit_enabled=True,
        amt_enabled=True,
    )


def test_compute_federal_income_tax_progressive():
    tax = compute_federal_income_tax(100_000, "single", 2026)
    assert 16_000 < tax < 18_000


def test_compute_capital_gains_tax_accounts_for_ordinary_income():
    low_other = compute_capital_gains_tax(50_000, 10_000, "single", 2026)
    high_other = compute_capital_gains_tax(50_000, 120_000, "single", 2026)
    assert high_other > low_other


def test_compute_total_tax_with_overrides():
    settings = _default_tax_settings()
    settings.federal_effective_rate_override = 0.20
    settings.state_effective_rate_override = 0.05
    settings.capital_gains_rate_override = 0.15
    settings.amt_enabled = False
    settings.niit_enabled = False

    result = compute_total_tax(
        YearIncomeSummary(
            year=2026,
            filing_status="married_filing_jointly",
            state="CA",
            ordinary_income=200_000,
            capital_gains=20_000,
            qualified_dividends=0,
            investment_income=20_000,
            itemized_deductions=0,
            withheld_tax=0,
            early_withdrawal_penalty=1_000,
        ),
        settings,
    )

    assert round(result.federal_income_tax, 2) == 33_560.00
    assert round(result.state_income_tax, 2) == 8_390.00
    assert round(result.capital_gains_tax, 2) == 3_000.00
    assert round(result.early_withdrawal_penalty, 2) == 1_000.00
    assert round(result.total_tax, 2) == 45_950.00


def test_niit_uses_combined_investment_base():
    settings = _default_tax_settings()
    settings.amt_enabled = False
    settings.state_effective_rate_override = 0.0
    settings.federal_effective_rate_override = 0.0
    settings.capital_gains_rate_override = 0.0

    result = compute_total_tax(
        YearIncomeSummary(
            year=2026,
            filing_status="single",
            state="CA",
            ordinary_income=250_000,
            capital_gains=40_000,
            qualified_dividends=10_000,
            investment_income=20_000,
            itemized_deductions=0,
        ),
        settings,
    )

    # NIIT base = min(20k + 50k, AGI-threshold(100k)) = 70k
    assert round(result.niit_tax, 2) == 2660.00


def test_fica_additional_medicare_uses_joint_threshold():
    single = compute_fica(300_000, 0, 2026, filing_status="single")
    mfj = compute_fica(300_000, 0, 2026, filing_status="married_filing_jointly")
    assert mfj < single


def test_2026_tax_data_uses_current_baselines():
    assert FEDERAL_BRACKETS[2026]["single"][1][0] == 50_400.0
    assert CAPITAL_GAINS_BRACKETS[2026]["single"][0][0] == 50_800.0
    assert STANDARD_DEDUCTIONS[2026]["single"] == 16_100.0
    assert STANDARD_DEDUCTIONS[2026]["married_filing_jointly"] == 32_200.0
    assert FICA_RATES[2026]["social_security_wage_base"] == 184_500.0


def test_state_tax_uses_progressive_brackets():
    low = compute_state_tax(50_000, "CA", "single", 2026)
    high = compute_state_tax(250_000, "CA", "single", 2026)
    assert high > low
    assert (high / 250_000) > (low / 50_000)


def test_state_tax_preserves_flat_tax_states():
    tax = compute_state_tax(100_000, "PA", "single", 2026)
    assert round(tax, 2) == 3070.00


def test_invalid_filing_status_raises():
    settings = _default_tax_settings()
    with pytest.raises(ValueError, match="unsupported filing_status"):
        compute_total_tax(
            YearIncomeSummary(
                year=2026,
                filing_status="bad_status",
                state="CA",
                ordinary_income=10_000,
                capital_gains=0,
            ),
            settings,
        )


def test_bracket_year_applies_when_not_using_current_brackets():
    settings_current = _default_tax_settings()
    settings_current.niit_enabled = False
    settings_current.amt_enabled = False
    settings_current.state_effective_rate_override = 0.0
    settings_current.capital_gains_rate_override = 0.0

    settings_alt = _default_tax_settings()
    settings_alt.use_current_brackets = False
    settings_alt.bracket_year = 2030
    settings_alt.niit_enabled = False
    settings_alt.amt_enabled = False
    settings_alt.state_effective_rate_override = 0.0
    settings_alt.capital_gains_rate_override = 0.0

    summary = YearIncomeSummary(
        year=2026,
        filing_status="single",
        state="CA",
        ordinary_income=150_000,
        capital_gains=0,
    )
    current_tax = compute_total_tax(summary, settings_current).total_tax
    alt_tax = compute_total_tax(summary, settings_alt).total_tax

    assert alt_tax > current_tax


def test_bracket_year_ignored_when_use_current_brackets_enabled():
    settings_default = _default_tax_settings()
    settings_default.bracket_year = 2026
    settings_default.niit_enabled = False
    settings_default.amt_enabled = False
    settings_default.state_effective_rate_override = 0.0
    settings_default.capital_gains_rate_override = 0.0

    settings_other_year = _default_tax_settings()
    settings_other_year.bracket_year = 2040
    settings_other_year.use_current_brackets = True
    settings_other_year.niit_enabled = False
    settings_other_year.amt_enabled = False
    settings_other_year.state_effective_rate_override = 0.0
    settings_other_year.capital_gains_rate_override = 0.0

    summary = YearIncomeSummary(
        year=2026,
        filing_status="single",
        state="CA",
        ordinary_income=150_000,
        capital_gains=0,
    )

    tax_default = compute_total_tax(summary, settings_default).total_tax
    tax_other = compute_total_tax(summary, settings_other_year).total_tax
    assert round(tax_default, 6) == round(tax_other, 6)
