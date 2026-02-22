from tfp.roth import execute_roth_conversions
from tfp.schema import RothConversion


def test_fixed_roth_conversion_monthly_prorata():
    balances = {"Trad": 12000.0, "Roth": 0.0}
    conversion = RothConversion(
        name="Fixed",
        from_account="Trad",
        to_account="Roth",
        annual_amount=12000.0,
        start_date="2026-01",
        end_date="2026-12",
        fill_to_bracket=None,
    )

    converted, ordinary = execute_roth_conversions(
        conversions=[conversion],
        balances=balances,
        current_year=2026,
        current_month=1,
        current_index=2026 * 12 + 1,
        plan_start="2026-01",
        plan_end="2026-12",
        filing_status="single",
        inflation_rate=0.03,
        ytd_taxable_ordinary_income=0.0,
    )

    assert converted == 1000.0
    assert ordinary == 1000.0
    assert balances["Trad"] == 11000.0
    assert balances["Roth"] == 1000.0


def test_fill_to_bracket_runs_in_december_only():
    balances = {"Trad": 10000.0, "Roth": 0.0}
    conversion = RothConversion(
        name="Fill 22",
        from_account="Trad",
        to_account="Roth",
        annual_amount=None,
        start_date="2026-01",
        end_date="2026-12",
        fill_to_bracket="22%",
    )

    nov_converted, _ = execute_roth_conversions(
        conversions=[conversion],
        balances=balances,
        current_year=2026,
        current_month=11,
        current_index=2026 * 12 + 11,
        plan_start="2026-01",
        plan_end="2026-12",
        filing_status="single",
        inflation_rate=0.03,
        ytd_taxable_ordinary_income=100000.0,
    )
    assert nov_converted == 0.0

    dec_converted, dec_ordinary = execute_roth_conversions(
        conversions=[conversion],
        balances=balances,
        current_year=2026,
        current_month=12,
        current_index=2026 * 12 + 12,
        plan_start="2026-01",
        plan_end="2026-12",
        filing_status="single",
        inflation_rate=0.03,
        ytd_taxable_ordinary_income=100000.0,
    )

    # 2026 single 22% bracket upper bound is 103,350.
    assert dec_converted == 3350.0
    assert dec_ordinary == 3350.0
