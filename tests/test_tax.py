from tfp.schema import ItemizedDeductions, TaxSettings
from tfp.tax import (
    YearIncomeSummary,
    compute_capital_gains_tax,
    compute_federal_income_tax,
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

    assert round(result.federal_income_tax, 2) == 34_000.00
    assert round(result.state_income_tax, 2) == 8_500.00
    assert round(result.capital_gains_tax, 2) == 3_000.00
    assert round(result.early_withdrawal_penalty, 2) == 1_000.00
    assert round(result.total_tax, 2) == 46_500.00
