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
from .validate import check_plan_sanity, validate_plan


def _money(value: float) -> str:
    return f"${value:,.0f}"


def _tooltip_text(lines: list[str]) -> str:
    if not lines:
        return "No detailed breakdown recorded."
    return "\n".join(lines)


def _money_cell(value: float, tooltip_lines: list[str]) -> str:
    tooltip = html.escape(_tooltip_text(tooltip_lines), quote=True)
    return f'<td title="{tooltip}">{_money(value)}</td>'


def _format_signed(value: float) -> str:
    return f"+{_money(value)}" if value > 0 else _money(value)


def _account_reason_lines(reason_map: dict[str, float]) -> list[str]:
    if not reason_map:
        return []
    lines: list[str] = []
    for label, amount in sorted(reason_map.items(), key=lambda item: abs(item[1]), reverse=True):
        if abs(amount) <= 0.01:
            continue
        lines.append(f"{label}: {_format_signed(amount)}")
    return lines


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


def _calculation_log_table(detail: EngineResult) -> str:
    rows: list[str] = []
    for row in detail.monthly:
        ym = f"{row.year:04d}-{row.month:02d}"
        sources = ", ".join(f"{name}: {_money(amount)}" for name, amount in sorted(row.withdrawal_sources.items()))
        if not sources:
            sources = "-"
        reasons = row.calculation_reasons
        rows.append(
            "<tr>"
            + f"<td>{ym}</td>"
            + _money_cell(row.income, reasons.get("income", []))
            + _money_cell(row.tax_withheld, reasons.get("tax_withheld", []))
            + _money_cell(row.contributions, reasons.get("contributions", []))
            + _money_cell(row.transfers, reasons.get("transfers", []))
            + _money_cell(row.healthcare_expenses, reasons.get("healthcare_expenses", []))
            + _money_cell(row.other_expenses + row.real_asset_expenses, reasons.get("other_expenses", []))
            + _money_cell(row.withdrawals, reasons.get("withdrawals", []))
            + _money_cell(row.realized_capital_gains, reasons.get("realized_capital_gains", []))
            + _money_cell(row.growth, reasons.get("growth", []))
            + _money_cell(row.dividends, reasons.get("dividends", []))
            + _money_cell(row.fees, reasons.get("fees", []))
            + _money_cell(row.tax_settlement, reasons.get("tax_settlement", []))
            + _money_cell(row.net_worth_end, reasons.get("net_worth_end", []))
            + f"<td>{html.escape(sources)}</td>"
            + f"<td>{'YES' if row.insolvent else ''}</td>"
            + "</tr>"
        )
    table_html = (
        "<table><thead><tr>"
        "<th>Month</th><th>Income</th><th>Withholding</th><th>Contrib</th><th>Transfers</th>"
        "<th>Healthcare</th><th>Other Exp</th><th>Withdrawals</th><th>Cap Gains</th><th>Growth</th>"
        "<th>Dividends</th><th>Fees</th><th>Tax Settle</th><th>Net Worth</th><th>Withdrawal Sources</th><th>Insolvent</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )
    return f'<div class="table-wrap calc-log">{table_html}</div>'


def _monthly_tax_table(detail: EngineResult) -> str:
    rows: list[str] = []
    for row in detail.monthly:
        ym = f"{row.year:04d}-{row.month:02d}"
        reasons = row.calculation_reasons
        net_tax_paid = row.tax_withheld + row.tax_estimated_payment + row.tax_settlement
        rows.append(
            "<tr>"
            + f"<td>{ym}</td>"
            + _money_cell(row.tax_fica_withheld, reasons.get("tax_withheld", []))
            + _money_cell(row.tax_income_withheld, reasons.get("tax_withheld", []))
            + _money_cell(row.tax_estimated_payment, reasons.get("tax_estimated", []))
            + _money_cell(row.tax_settlement, reasons.get("tax_settlement", []))
            + _money_cell(net_tax_paid, reasons.get("tax_settlement", []) + reasons.get("tax_estimated", []))
            + "</tr>"
        )
    table_html = (
        "<table><thead><tr>"
        "<th>Month</th><th>FICA Withheld</th><th>Income Tax Withheld</th>"
        "<th>Estimated Tax Payment</th><th>Year-End Settlement (+pay / -refund)</th><th>Net Tax Cash Flow</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )
    return f'<div class="table-wrap">{table_html}</div>'


def _validation_panel(plan: Plan) -> str:
    validation = validate_plan(plan)
    sanity = check_plan_sanity(plan)

    rows: list[str] = []
    for msg in validation.errors:
        rows.append(f"<tr><td>Error</td><td>{html.escape(msg)}</td></tr>")
    for msg in validation.warnings:
        rows.append(f"<tr><td>Validation warning</td><td>{html.escape(msg)}</td></tr>")
    for msg in sanity.warnings:
        rows.append(f"<tr><td>Sanity warning</td><td>{html.escape(msg)}</td></tr>")
    if not rows:
        rows.append("<tr><td>OK</td><td>No validation/sanity issues detected.</td></tr>")

    return (
        "<table><thead><tr><th>Type</th><th>Detail</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _account_balance_monthly_table(plan: Plan, detail: EngineResult) -> str:
    account_names = [account.name for account in plan.accounts]
    header_cells = "".join(f"<th>{html.escape(name)}</th>" for name in account_names)

    rows: list[str] = []
    for month in detail.monthly:
        ym = f"{month.year:04d}-{month.month:02d}"
        balance_cells = "".join(
            f"<td>{_money(month.account_balances_end.get(name, 0.0))}</td>"
            for name in account_names
        )
        rows.append(f"<tr><td>{ym}</td>{balance_cells}</tr>")

    table_html = (
        "<table><thead><tr><th>Month</th>"
        + header_cells
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )
    return f'<div class="table-wrap">{table_html}</div>'


def _account_flow_monthly_table(plan: Plan, detail: EngineResult) -> str:
    account_names = [account.name for account in plan.accounts]
    prev_balances = {account.name: float(account.balance) for account in plan.accounts}
    header_cells = "".join(f"<th>{html.escape(name)}</th>" for name in account_names)

    rows: list[str] = []
    for month in detail.monthly:
        ym = f"{month.year:04d}-{month.month:02d}"
        cells: list[str] = []
        for name in account_names:
            current = float(month.account_balances_end.get(name, 0.0))
            delta = current - prev_balances.get(name, 0.0)
            prev_balances[name] = current
            tooltip_lines = _account_reason_lines(month.account_flow_reasons.get(name, {}))
            cells.append(_money_cell(delta, tooltip_lines))
        rows.append(f"<tr><td>{ym}</td>{''.join(cells)}</tr>")

    table_html = (
        "<table><thead><tr><th>Month</th>"
        + header_cells
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )
    return f'<div class="table-wrap">{table_html}</div>'


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
        account_balance_table=_account_balance_monthly_table(plan, detail),
        account_flow_table=_account_flow_monthly_table(plan, detail),
        tax_table=_monthly_tax_table(detail),
        calc_log_table=_calculation_log_table(detail),
        validation_table=_validation_panel(plan),
        payload_json=json.dumps(payload),
    )


def write_report(path: str | Path, html_content: str) -> None:
    Path(path).write_text(html_content, encoding="utf-8")
