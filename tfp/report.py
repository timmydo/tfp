"""HTML report generation."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import html
import json
from pathlib import Path

from .charts import build_chart_payload
from .engine import EngineResult, run_deterministic
from .sankey import build_sankey_payload
from .schema import Plan
from .simulation import SimulationResult
from .templates import render_html_document


def _money(value: float) -> str:
    return f"${value:,.0f}"


def _dashboard_cards(result: SimulationResult, detail: EngineResult) -> str:
    start_year = result.annual[0].year if result.annual else None
    end_year = result.annual[-1].year if result.annual else None
    ending = result.annual[-1].net_worth_end if result.annual else 0.0
    total_income = sum(row.income for row in result.annual)
    total_expenses = sum(row.expenses for row in result.annual)
    avg_tax = sum((row.tax_total if row.tax_total > 0 else row.tax_withheld) for row in detail.annual) / max(1, len(detail.annual))
    success_rate = 0.0 if result.success_rate is None else result.success_rate * 100.0

    cards = [
        ("Years", f"{start_year}-{end_year}"),
        ("Ending Net Worth", _money(ending)),
        ("Success Rate", f"{success_rate:.1f}%"),
        ("Total Income", _money(total_income)),
        ("Total Expenses", _money(total_expenses)),
        ("Avg Annual Tax", _money(avg_tax)),
    ]
    return "".join(f'<div class="card"><div class="k">{html.escape(k)}</div><div class="v">{html.escape(v)}</div></div>' for k, v in cards)


def _annual_summary_table(result: SimulationResult, detail: EngineResult) -> str:
    by_year = {row.year: row for row in detail.annual}
    rows: list[str] = []
    for row in result.annual:
        d = by_year.get(row.year)
        taxes = (d.tax_total if d and d.tax_total > 0 else (d.tax_withheld if d else 0.0))
        insolvent = "insolvent" if row.year in result.insolvency_years else ""
        note = "Insolvent" if row.year in result.insolvency_years else ""
        rows.append(
            "<tr class=\"{}\">".format(insolvent)
            + f"<td>{row.year}</td>"
            + f"<td>{_money(row.income)}</td>"
            + f"<td>{_money(row.expenses)}</td>"
            + f"<td>{_money(taxes)}</td>"
            + f"<td>{_money(d.withdrawals if d else 0.0)}</td>"
            + f"<td>{_money(d.contributions if d else 0.0)}</td>"
            + f"<td>{_money(row.net_worth_end)}</td>"
            + f"<td>{html.escape(note)}</td>"
            + "</tr>"
        )

    return (
        "<table><thead><tr>"
        "<th>Year</th><th>Income</th><th>Expenses</th><th>Taxes</th><th>Withdrawals</th><th>Contributions</th><th>Net Worth</th><th>Notes</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _money_flow_table(detail: EngineResult) -> str:
    rows = []
    for annual in detail.annual:
        expenses = annual.healthcare_expenses + annual.other_expenses + annual.real_asset_expenses
        taxes = annual.tax_total if annual.tax_total > 0 else annual.tax_withheld
        rows.append(
            "<tr>"
            + f"<td>{annual.year}</td>"
            + f"<td>{_money(annual.income)}</td>"
            + f"<td>{_money(annual.withdrawals)}</td>"
            + f"<td>{_money(annual.tax_refund)}</td>"
            + f"<td>{_money(expenses)}</td>"
            + f"<td>{_money(taxes)}</td>"
            + f"<td>{_money(annual.contributions)}</td>"
            + f"<td>{_money(annual.transfers)}</td>"
            + "</tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>Year</th><th>Income</th><th>Withdrawals</th><th>Refunds</th><th>Expenses</th><th>Taxes</th><th>Contributions</th><th>Transfers</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _account_detail_tables(detail: EngineResult) -> str:
    sections: list[str] = []
    for account_name in sorted(detail.account_annual):
        rows = []
        for row in detail.account_annual[account_name]:
            rows.append(
                "<tr>"
                + f"<td>{row.year}</td>"
                + f"<td>{_money(row.starting_balance)}</td>"
                + f"<td>{_money(row.growth)}</td>"
                + f"<td>{_money(row.dividends)}</td>"
                + f"<td>{_money(row.contributions)}</td>"
                + f"<td>{_money(row.withdrawals)}</td>"
                + f"<td>{_money(row.fees)}</td>"
                + f"<td>{_money(row.ending_balance)}</td>"
                + "</tr>"
            )
        sections.append(
            f"<h3>{html.escape(account_name)}</h3>"
            + "<table><thead><tr>"
            + "<th>Year</th><th>Starting</th><th>Growth</th><th>Dividends</th><th>Contributions</th><th>Withdrawals</th><th>Fees</th><th>Ending</th>"
            + "</tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )
    return "".join(sections)


def _report_payload(plan: Plan, result: SimulationResult, detail: EngineResult) -> dict[str, object]:
    return {
        "mode": result.mode,
        "seed": result.seed,
        "scenario_count": result.scenario_count,
        "success_rate": result.success_rate,
        "insolvency_years": result.insolvency_years,
        "annual": [asdict(row) for row in result.annual],
        "charts": build_chart_payload(plan, result, detail),
        "sankey": build_sankey_payload(detail),
    }


def render_report(plan: Plan, result: SimulationResult, plan_path: str) -> str:
    detail = run_deterministic(plan)
    payload = _report_payload(plan, result, detail)

    plan_hash = hashlib.sha256(Path(plan_path).read_bytes()).hexdigest()[:12]
    title = f"TFP Report - {html.escape(plan.people.primary.name)}"
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    subtitle = (
        f"Mode: {html.escape(result.mode)} | Seed: {result.seed} | Generated: {timestamp} | "
        f"Plan hash: {plan_hash}"
    )

    return render_html_document(
        title=title,
        subtitle=subtitle,
        dashboard_cards=_dashboard_cards(result, detail),
        annual_table=_annual_summary_table(result, detail),
        flow_table=_money_flow_table(detail),
        account_tables=_account_detail_tables(detail),
        payload_json=json.dumps(payload),
    )


def write_report(path: str | Path, html_content: str) -> None:
    Path(path).write_text(html_content, encoding="utf-8")
