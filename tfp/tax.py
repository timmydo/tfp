"""Tax computation helpers for federal/state/FICA calculations."""

from __future__ import annotations

from dataclasses import dataclass

from .schema import TaxSettings
from .tax_data import (
    AMT_BRACKETS,
    AMT_EXEMPTIONS,
    BASE_TAX_YEAR,
    CAPITAL_GAINS_BRACKETS,
    DEFAULT_BRACKET_INFLATION,
    FEDERAL_BRACKETS,
    FICA_RATES,
    NIIT_THRESHOLDS,
    STANDARD_DEDUCTIONS,
    STATE_EFFECTIVE_RATES,
)


@dataclass(slots=True)
class YearIncomeSummary:
    year: int
    filing_status: str
    state: str
    ordinary_income: float
    capital_gains: float
    qualified_dividends: float = 0.0
    investment_income: float = 0.0
    itemized_deductions: float = 0.0
    withheld_tax: float = 0.0
    early_withdrawal_penalty: float = 0.0


@dataclass(slots=True)
class TaxResult:
    federal_income_tax: float
    capital_gains_tax: float
    niit_tax: float
    amt_tax: float
    state_income_tax: float
    early_withdrawal_penalty: float
    total_tax: float
    deduction_used: float
    taxable_ordinary_income: float


def _year_factor(year: int, inflation_rate: float) -> float:
    delta = max(0, year - BASE_TAX_YEAR)
    return (1.0 + inflation_rate) ** delta


def _normalize_filing_status(filing_status: str) -> str:
    if filing_status in FEDERAL_BRACKETS[BASE_TAX_YEAR]:
        return filing_status
    return "single"


def _adjusted_standard_deduction(filing_status: str, year: int, inflation_rate: float) -> float:
    fs = _normalize_filing_status(filing_status)
    base = STANDARD_DEDUCTIONS[BASE_TAX_YEAR][fs]
    return base * _year_factor(year, inflation_rate)


def _adjusted_brackets(
    brackets_by_year: dict[int, dict[str, list[tuple[float | None, float]]]],
    filing_status: str,
    year: int,
    inflation_rate: float,
) -> list[tuple[float | None, float]]:
    fs = _normalize_filing_status(filing_status)
    base = brackets_by_year[BASE_TAX_YEAR][fs]
    factor = _year_factor(year, inflation_rate)
    return [(None if upper is None else upper * factor, rate) for upper, rate in base]


def _progressive_tax(amount: float, brackets: list[tuple[float | None, float]]) -> float:
    if amount <= 0:
        return 0.0

    remaining = amount
    lower = 0.0
    tax = 0.0
    for upper, rate in brackets:
        if remaining <= 0:
            break
        if upper is None:
            taxable_at_rate = remaining
        else:
            span = max(0.0, upper - lower)
            taxable_at_rate = min(remaining, span)
        tax += taxable_at_rate * rate
        remaining -= taxable_at_rate
        if upper is None:
            break
        lower = upper
    return max(0.0, tax)


def compute_federal_income_tax(taxable_income: float, filing_status: str, year: int, inflation_rate: float = DEFAULT_BRACKET_INFLATION) -> float:
    brackets = _adjusted_brackets(FEDERAL_BRACKETS, filing_status, year, inflation_rate)
    return _progressive_tax(taxable_income, brackets)


def _capital_gains_zero_bracket_room(
    ordinary_taxable_income: float,
    filing_status: str,
    year: int,
    inflation_rate: float,
) -> float:
    brackets = _adjusted_brackets(CAPITAL_GAINS_BRACKETS, filing_status, year, inflation_rate)
    zero_cap = brackets[0][0] or 0.0
    return max(0.0, zero_cap - max(0.0, ordinary_taxable_income))


def compute_capital_gains_tax(
    gains: float,
    other_taxable_income: float,
    filing_status: str,
    year: int,
    inflation_rate: float = DEFAULT_BRACKET_INFLATION,
) -> float:
    if gains <= 0:
        return 0.0

    brackets = _adjusted_brackets(CAPITAL_GAINS_BRACKETS, filing_status, year, inflation_rate)
    remaining_gains = gains
    tax = 0.0

    zero_room = _capital_gains_zero_bracket_room(other_taxable_income, filing_status, year, inflation_rate)
    zero_bucket = min(remaining_gains, zero_room)
    remaining_gains -= zero_bucket

    lower = brackets[0][0] or 0.0
    for upper, rate in brackets[1:]:
        if remaining_gains <= 0:
            break

        if upper is None:
            taxable_at_rate = remaining_gains
        else:
            effective_upper = max(upper, other_taxable_income)
            effective_span = max(0.0, effective_upper - max(other_taxable_income, lower))
            taxable_at_rate = min(remaining_gains, effective_span)

        tax += taxable_at_rate * rate
        remaining_gains -= taxable_at_rate
        if upper is not None:
            lower = upper

    if remaining_gains > 0:
        tax += remaining_gains * 0.20
    return max(0.0, tax)


def compute_niit(
    investment_income: float,
    agi: float,
    filing_status: str,
    year: int,
    inflation_rate: float = DEFAULT_BRACKET_INFLATION,
) -> float:
    if investment_income <= 0:
        return 0.0

    fs = _normalize_filing_status(filing_status)
    threshold = NIIT_THRESHOLDS[fs] * _year_factor(year, inflation_rate)
    excess_agi = max(0.0, agi - threshold)
    taxable_base = min(max(0.0, investment_income), excess_agi)
    return taxable_base * 0.038


def compute_amt(
    income: float,
    deductions: float,
    filing_status: str,
    year: int,
    inflation_rate: float = DEFAULT_BRACKET_INFLATION,
) -> float:
    fs = _normalize_filing_status(filing_status)
    exemption, phaseout_start = AMT_EXEMPTIONS[fs]
    factor = _year_factor(year, inflation_rate)
    exemption *= factor
    phaseout_start *= factor

    tentative_amt_income = max(0.0, income - max(0.0, deductions))
    if tentative_amt_income > phaseout_start:
        exemption = max(0.0, exemption - 0.25 * (tentative_amt_income - phaseout_start))

    amt_taxable = max(0.0, tentative_amt_income - exemption)
    return _progressive_tax(amt_taxable, AMT_BRACKETS)


def compute_state_tax(
    taxable_income: float,
    state: str,
    filing_status: str,
    year: int,
    inflation_rate: float = DEFAULT_BRACKET_INFLATION,
) -> float:
    _ = filing_status
    rates = STATE_EFFECTIVE_RATES[BASE_TAX_YEAR]
    rate = rates.get(state.upper(), 0.0)
    _ = year, inflation_rate
    return max(0.0, taxable_income) * rate


def compute_fica(wages: float, ytd_wages: float, year: int, inflation_rate: float = DEFAULT_BRACKET_INFLATION) -> float:
    if wages <= 0:
        return 0.0

    base = FICA_RATES[BASE_TAX_YEAR]
    factor = _year_factor(year, inflation_rate)
    ss_rate = base["social_security_rate"]
    ss_wage_base = base["social_security_wage_base"] * factor
    medicare_rate = base["medicare_rate"]
    additional_rate = base["additional_medicare_rate"]
    additional_threshold = base["additional_medicare_single_threshold"] * factor

    ss_taxable = max(0.0, min(wages, ss_wage_base - max(0.0, ytd_wages)))
    ss_tax = ss_taxable * ss_rate
    medicare_tax = wages * medicare_rate

    additional_taxable = max(0.0, (ytd_wages + wages) - additional_threshold)
    additional_taxable -= max(0.0, ytd_wages - additional_threshold)
    additional_tax = max(0.0, additional_taxable) * additional_rate

    return ss_tax + medicare_tax + additional_tax


def compute_self_employment_tax(se_income: float, year: int, inflation_rate: float = DEFAULT_BRACKET_INFLATION) -> float:
    if se_income <= 0:
        return 0.0

    base = FICA_RATES[BASE_TAX_YEAR]
    factor = _year_factor(year, inflation_rate)
    ss_wage_base = base["social_security_wage_base"] * factor

    taxable = se_income * 0.9235
    ss_part = min(max(0.0, taxable), ss_wage_base) * (base["social_security_rate"] * 2.0)
    medicare_part = taxable * (base["medicare_rate"] * 2.0)
    return ss_part + medicare_part


def compute_standard_vs_itemized(
    filing_status: str,
    year: int,
    itemized_details: float,
    standard_override: float | None,
    inflation_rate: float = DEFAULT_BRACKET_INFLATION,
) -> float:
    standard = standard_override
    if standard is None:
        standard = _adjusted_standard_deduction(filing_status, year, inflation_rate)
    return max(0.0, max(standard, itemized_details))


def compute_total_tax(
    summary: YearIncomeSummary,
    tax_settings: TaxSettings,
    inflation_rate: float = DEFAULT_BRACKET_INFLATION,
) -> TaxResult:
    filing_status = _normalize_filing_status(summary.filing_status)
    ordinary_income = max(0.0, summary.ordinary_income)
    capital_gains = max(0.0, summary.capital_gains)
    qualified_dividends = max(0.0, summary.qualified_dividends)
    investment_income = max(0.0, summary.investment_income)

    deduction = compute_standard_vs_itemized(
        filing_status,
        summary.year,
        summary.itemized_deductions,
        tax_settings.standard_deduction_override,
        inflation_rate,
    )

    taxable_ordinary = max(0.0, ordinary_income - deduction)

    if tax_settings.federal_effective_rate_override is not None:
        federal_tax = taxable_ordinary * max(0.0, tax_settings.federal_effective_rate_override)
    else:
        federal_tax = compute_federal_income_tax(taxable_ordinary, filing_status, summary.year, inflation_rate)

    gross_ltcg = capital_gains + qualified_dividends
    if tax_settings.capital_gains_rate_override is not None:
        cap_tax = gross_ltcg * max(0.0, tax_settings.capital_gains_rate_override)
    else:
        cap_tax = compute_capital_gains_tax(gross_ltcg, taxable_ordinary, filing_status, summary.year, inflation_rate)

    agi = ordinary_income + gross_ltcg

    niit_tax = 0.0
    if tax_settings.niit_enabled:
        niit_base = max(investment_income, gross_ltcg)
        niit_tax = compute_niit(niit_base, agi, filing_status, summary.year, inflation_rate)

    amt_tax = 0.0
    if tax_settings.amt_enabled:
        tentative_amt = compute_amt(agi, deduction, filing_status, summary.year, inflation_rate)
        regular_tax = federal_tax + cap_tax
        amt_tax = max(0.0, tentative_amt - regular_tax)

    if tax_settings.state_effective_rate_override is not None:
        state_tax = max(0.0, taxable_ordinary * tax_settings.state_effective_rate_override)
    else:
        state_tax = compute_state_tax(taxable_ordinary, summary.state, filing_status, summary.year, inflation_rate)

    total = federal_tax + cap_tax + niit_tax + amt_tax + state_tax + max(0.0, summary.early_withdrawal_penalty)
    return TaxResult(
        federal_income_tax=max(0.0, federal_tax),
        capital_gains_tax=max(0.0, cap_tax),
        niit_tax=max(0.0, niit_tax),
        amt_tax=max(0.0, amt_tax),
        state_income_tax=max(0.0, state_tax),
        early_withdrawal_penalty=max(0.0, summary.early_withdrawal_penalty),
        total_tax=max(0.0, total),
        deduction_used=max(0.0, deduction),
        taxable_ordinary_income=max(0.0, taxable_ordinary),
    )
