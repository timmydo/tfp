import re

from tests.helpers import clone_plan, write_plan
from tfp.__main__ import main


def test_report_html_includes_required_sections(tmp_path):
    output_path = tmp_path / "report.html"
    code = main(["sample_plan.json", "--mode", "deterministic", "-o", str(output_path)])

    assert code == 0
    text = output_path.read_text(encoding="utf-8")

    assert "Overview" in text
    assert "Annual Financials" in text
    assert "Account Details" in text
    assert "Account Balance View" in text
    assert "Account Activity View" in text
    assert "Taxes" in text
    assert "Calculation Log" in text
    assert "Plan Validation" in text

    assert 'id="tab-flows"' in text
    assert 'id="tab-tables"' not in text
    assert 'id="tab-account-balances"' in text
    assert 'id="tab-account-flows"' in text
    assert 'id="tab-taxes"' in text
    assert 'id="tab-calc-log"' in text
    assert 'id="tab-validation"' in text
    assert 'id="tab-overview"' in text
    assert "Input Overview" in text
    assert "Full normalized plan JSON used for calculations" in text
    assert "Mode:" in text
    assert "Plan hash:" in text
    assert "Dashboard" not in text
    assert "Charts" not in text
    assert "sankey-year" not in text
    assert "chart-" not in text

    # Self-contained output: no remote script/style references.
    assert "https://" not in text
    assert "http://" not in text


def test_insolvency_years_are_highlighted_in_report(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2028-12"
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
            "balance": 1000,
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
    data["withdrawal_strategy"] = {
        "order": ["cash"],
        "account_specific_order": ["Cash"],
        "use_account_specific": True,
        "rmd_satisfied_first": True,
    }
    data["expenses"] = [
        {
            "name": "Huge expense",
            "owner": "joint",
            "amount": 50000,
            "frequency": "monthly",
            "start_date": "start",
            "end_date": "end",
            "change_over_time": "fixed",
            "change_rate": None,
            "spending_type": "essential",
        }
    ]

    plan_path = write_plan(tmp_path, data)
    output_path = tmp_path / "report.html"
    code = main([str(plan_path), "--mode", "deterministic", "-o", str(output_path)])

    assert code == 0
    text = output_path.read_text(encoding="utf-8")
    assert "class=\"insolvent\"" in text


def test_account_details_shows_prior_year_delta_before_balance(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2027-12"

    plan_path = write_plan(tmp_path, data)
    output_path = tmp_path / "report.html"
    code = main([str(plan_path), "--mode", "deterministic", "-o", str(output_path)])

    assert code == 0
    text = output_path.read_text(encoding="utf-8")
    assert 'class="cell-delta"' in text
    assert re.search(r'class="cell-delta">[+\-]?\$[0-9,]+</div><div class="cell-main">\$[0-9,]+</div>', text)


def test_account_balance_view_chart_and_monthly_table_values(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2026-03"
    data["income"] = []
    data["contributions"] = []
    data["transfers"] = []
    data["transactions"] = []
    data["real_assets"] = []
    data["healthcare"]["pre_medicare"] = []
    data["healthcare"]["post_medicare"] = []
    data["social_security"] = []
    data["expenses"] = []
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
            "name": "Brokerage",
            "type": "taxable_brokerage",
            "owner": "primary",
            "balance": 2000,
            "cost_basis": 2000,
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
        "account_specific_order": ["Cash", "Brokerage"],
        "use_account_specific": True,
        "rmd_satisfied_first": True,
    }

    plan_path = write_plan(tmp_path, data)
    output_path = tmp_path / "report.html"
    code = main([str(plan_path), "--mode", "deterministic", "-o", str(output_path)])
    assert code == 0

    text = output_path.read_text(encoding="utf-8")
    assert "<td>2026-01</td><td>$1,000</td><td>$2,000</td>" in text
    assert "<td>2026-02</td><td>$1,000</td><td>$2,000</td>" in text
    assert "<td>2026-03</td><td>$1,000</td><td>$2,000</td>" in text

    assert "const payload =" not in text


def test_account_flow_view_chart_and_monthly_table_values(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2026-03"
    data["income"] = []
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
            "name": "Brokerage",
            "type": "taxable_brokerage",
            "owner": "primary",
            "balance": 2000,
            "cost_basis": 2000,
            "growth_rate": 0.0,
            "dividend_yield": 0.0,
            "dividend_tax_treatment": "capital_gains",
            "reinvest_dividends": True,
            "bond_allocation_percent": 0,
            "yearly_fees": 0.0,
            "allow_withdrawals": True,
        },
    ]
    data["expenses"] = [
        {
            "name": "Baseline spending",
            "owner": "joint",
            "amount": 100,
            "frequency": "monthly",
            "start_date": "start",
            "end_date": "end",
            "change_over_time": "fixed",
            "change_rate": None,
            "spending_type": "essential",
        }
    ]
    data["transfers"] = [
        {
            "name": "Move to brokerage",
            "from_account": "Cash",
            "to_account": "Brokerage",
            "amount": 300,
            "frequency": "one_time",
            "start_date": "2026-01",
            "end_date": "2026-01",
            "tax_treatment": "tax_free",
        }
    ]
    data["withdrawal_strategy"] = {
        "order": ["cash", "taxable_brokerage"],
        "account_specific_order": ["Cash", "Brokerage"],
        "use_account_specific": True,
        "rmd_satisfied_first": True,
    }

    plan_path = write_plan(tmp_path, data)
    output_path = tmp_path / "report.html"
    code = main([str(plan_path), "--mode", "deterministic", "-o", str(output_path)])
    assert code == 0

    text = output_path.read_text(encoding="utf-8")
    assert re.search(r"<td>2026-01</td>[\s\S]*?<div class=\"cell-main\">\$-400</div>[\s\S]*?<div class=\"cell-main\">\$300</div>", text)
    assert re.search(r"<td>2026-02</td>[\s\S]*?<div class=\"cell-main\">\$-100</div>[\s\S]*?<div class=\"cell-main\">\$0</div>", text)
    assert re.search(r"<td>2026-03</td>[\s\S]*?<div class=\"cell-main\">\$-100</div>[\s\S]*?<div class=\"cell-main\">\$0</div>", text)
    assert "Transfer out: Move to brokerage: $-300" in text
    assert "Transfer in: Move to brokerage: +$300" in text

    assert "const payload =" not in text


def test_annual_financials_contributions_do_not_show_account_inflows_when_total_is_zero(
    tmp_path,
    sample_plan_dict,
):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2027-12"
    data["contributions"] = []
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
            "withhold_percent": 0.2,
        }
    ]
    data["transfers"] = []
    data["transactions"] = []
    data["social_security"] = []
    data["roth_conversions"] = []
    data["rmds"] = {
        "enabled": False,
        "rmd_start_age": 73,
        "accounts": [],
        "destination_account": "Joint Checking",
    }

    plan_path = write_plan(tmp_path, data)
    output_path = tmp_path / "report.html"
    code = main([str(plan_path), "--mode", "deterministic", "-o", str(output_path)])
    assert code == 0

    text = output_path.read_text(encoding="utf-8")
    annual_table_match = re.search(
        r"<table><thead><tr><th>Year \(Age\)</th><th>Income</th><th>Expenses</th><th>Taxes</th><th>Withdrawals</th>"
        r"<th>Contributions</th><th>Transfers</th><th>Net Worth</th><th>Notes</th></tr></thead><tbody>(.*?)</tbody></table>",
        text,
        re.DOTALL,
    )
    assert annual_table_match is not None
    annual_rows_html = annual_table_match.group(1)
    row_match = re.search(r"<tr[^>]*>.*?<td>2026 \([^)]+\)</td>.*?</tr>", annual_rows_html, re.DOTALL)
    assert row_match is not None
    row_html = row_match.group(0)
    cells = re.findall(r"<td(?: [^>]*)?>.*?</td>", row_html)
    assert len(cells) >= 6
    contributions_cell = cells[5]

    assert "<div class=\"cell-main\">$0</div>" in contributions_cell
    assert "cell-breakdown" not in contributions_cell


def test_annual_financials_breaks_out_withheld_tax_and_cleans_contribution_prefixes(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2026-12"
    data["income"] = [
        {
            "name": "Salary",
            "owner": "primary",
            "amount": 180000,
            "frequency": "annual",
            "start_date": "start",
            "end_date": "end",
            "change_over_time": "fixed",
            "change_rate": None,
            "tax_handling": "withhold",
            "withhold_percent": 0.25,
        }
    ]
    data["contributions"] = [
        {
            "name": "Primary 401k contribution",
            "source_account": "income",
            "destination_account": "Alex 401k",
            "amount": 23500,
            "frequency": "annual",
            "start_date": "start",
            "end_date": "end",
            "change_over_time": "fixed",
            "change_rate": None,
            "employer_match": None,
        },
        {
            "name": "HSA contribution",
            "source_account": "income",
            "destination_account": "Family HSA",
            "amount": 8550,
            "frequency": "annual",
            "start_date": "start",
            "end_date": "end",
            "change_over_time": "fixed",
            "change_rate": None,
            "employer_match": None,
        },
    ]
    data["transfers"] = []
    data["transactions"] = []
    data["social_security"] = []
    data["roth_conversions"] = []
    data["rmds"] = {
        "enabled": False,
        "rmd_start_age": 73,
        "accounts": [],
        "destination_account": "Joint Checking",
    }

    plan_path = write_plan(tmp_path, data)
    output_path = tmp_path / "report.html"
    code = main([str(plan_path), "--mode", "deterministic", "-o", str(output_path)])
    assert code == 0

    text = output_path.read_text(encoding="utf-8")
    annual_table_match = re.search(
        r"<table><thead><tr><th>Year \(Age\)</th><th>Income</th><th>Expenses</th><th>Taxes</th><th>Withdrawals</th>"
        r"<th>Contributions</th><th>Transfers</th><th>Net Worth</th><th>Notes</th></tr></thead><tbody>(.*?)</tbody></table>",
        text,
        re.DOTALL,
    )
    assert annual_table_match is not None
    annual_rows_html = annual_table_match.group(1)
    row_match = re.search(r"<tr[^>]*>.*?<td>2026 \([^)]+\)</td>.*?</tr>", annual_rows_html, re.DOTALL)
    assert row_match is not None
    row_html = row_match.group(0)

    assert "Withheld (FICA): $" in row_html
    assert "Withheld (Income tax): $" in row_html
    assert "Contribution: Primary 401k contribution" not in row_html
    assert "Contribution: HSA contribution" not in row_html
    assert "Primary 401k contribution: $" in row_html
    assert "HSA contribution: $" in row_html


def test_money_flow_tooltips_include_expense_components_and_transfer_paths(tmp_path, sample_plan_dict):
    data = clone_plan(sample_plan_dict)
    data["plan_settings"]["plan_start"] = "2026-01"
    data["plan_settings"]["plan_end"] = "2026-12"
    data["income"] = []
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
            "name": "Brokerage",
            "type": "taxable_brokerage",
            "owner": "primary",
            "balance": 0,
            "cost_basis": 0,
            "growth_rate": 0.0,
            "dividend_yield": 0.0,
            "dividend_tax_treatment": "capital_gains",
            "reinvest_dividends": True,
            "bond_allocation_percent": 0,
            "yearly_fees": 0.0,
            "allow_withdrawals": True,
        },
    ]
    data["expenses"] = [
        {
            "name": "Groceries",
            "owner": "joint",
            "amount": 200,
            "frequency": "monthly",
            "start_date": "start",
            "end_date": "end",
            "change_over_time": "fixed",
            "change_rate": None,
            "spending_type": "essential",
        },
        {
            "name": "Travel",
            "owner": "joint",
            "amount": 1200,
            "frequency": "annual",
            "start_date": "start",
            "end_date": "end",
            "change_over_time": "fixed",
            "change_rate": None,
            "spending_type": "discretionary",
        },
    ]
    data["transfers"] = [
        {
            "name": "Fund brokerage",
            "from_account": "Cash",
            "to_account": "Brokerage",
            "amount": 300,
            "frequency": "monthly",
            "start_date": "start",
            "end_date": "end",
            "tax_treatment": "tax_free",
        }
    ]
    data["withdrawal_strategy"] = {
        "order": ["cash", "taxable_brokerage"],
        "account_specific_order": ["Cash", "Brokerage"],
        "use_account_specific": True,
        "rmd_satisfied_first": True,
    }

    plan_path = write_plan(tmp_path, data)
    output_path = tmp_path / "report.html"
    code = main([str(plan_path), "--mode", "deterministic", "-o", str(output_path)])
    assert code == 0

    text = output_path.read_text(encoding="utf-8")
    assert "Expense: Groceries: $2,400" in text
    assert "Expense: Travel: $1,200" in text
    assert "Transfer: Fund brokerage (Cash -&gt; Brokerage): $3,600" in text
