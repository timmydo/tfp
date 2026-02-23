import json
import re

from tests.helpers import clone_plan, write_plan
from tfp.__main__ import main


def test_report_html_includes_required_sections(tmp_path):
    output_path = tmp_path / "report.html"
    code = main(["sample_plan.json", "--mode", "deterministic", "-o", str(output_path)])

    assert code == 0
    text = output_path.read_text(encoding="utf-8")

    assert "Dashboard" in text
    assert "Charts" in text
    assert "Money Flows" in text
    assert "Tables" in text
    assert "Account Details" in text
    assert "Account Balance View" in text
    assert "Calculation Log" in text
    assert "Plan Validation" in text

    assert 'id="chart-net-worth"' in text
    assert 'id="chart-tax"' in text
    assert 'id="chart-sankey"' in text
    assert 'id="chart-account-balance-yearly"' in text
    assert 'id="tab-account-balances"' in text
    assert 'id="tab-calc-log"' in text
    assert 'id="tab-validation"' in text
    assert "Mode:" in text
    assert "Plan hash:" in text

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

    payload_match = re.search(r"const payload = (\{.*?\});", text, flags=re.DOTALL)
    assert payload_match is not None
    payload = json.loads(payload_match.group(1))
    assert payload["charts"]["years"] == [2026]
    assert payload["charts"]["accountBalances"]["Cash"] == [1000.0]
    assert payload["charts"]["accountBalances"]["Brokerage"] == [2000.0]
