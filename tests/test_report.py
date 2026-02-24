import re

from tests.helpers import clone_plan, write_plan
from tfp.__main__ import main


def test_report_html_includes_required_sections(tmp_path):
    output_path = tmp_path / "report.html"
    code = main(["sample_plan.json", "--mode", "deterministic", "-o", str(output_path)])

    assert code == 0
    text = output_path.read_text(encoding="utf-8")

    assert "Overview" in text
    assert "Money Flows" in text
    assert "Totals by Year" in text
    assert "Account Details" in text
    assert "Account Balance View" in text
    assert "Account Flow View" in text
    assert "Taxes" in text
    assert "Calculation Log" in text
    assert "Plan Validation" in text

    assert 'id="tab-flows"' in text
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
    assert re.search(r"<td>2026-01</td><td[^>]*>\$-400</td><td[^>]*>\$300</td>", text)
    assert re.search(r"<td>2026-02</td><td[^>]*>\$-100</td><td[^>]*>\$0</td>", text)
    assert re.search(r"<td>2026-03</td><td[^>]*>\$-100</td><td[^>]*>\$0</td>", text)
    assert "Transfer out: Move to brokerage: $-300" in text
    assert "Transfer in: Move to brokerage: +$300" in text

    assert "const payload =" not in text
