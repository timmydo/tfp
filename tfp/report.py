"""HTML report generation."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, UTC
import html
import json
from pathlib import Path
import hashlib

from .schema import Plan
from .simulation import SimulationResult


def render_report(plan: Plan, result: SimulationResult, plan_path: str) -> str:
    rows = "\n".join(
        (
            "<tr>"
            f"<td>{row.year}</td>"
            f"<td>${row.income:,.0f}</td>"
            f"<td>${row.expenses:,.0f}</td>"
            f"<td>${row.net_flow:,.0f}</td>"
            f"<td>${row.net_worth_end:,.0f}</td>"
            "</tr>"
        )
        for row in result.annual
    )
    payload = json.dumps(
        {
            "mode": result.mode,
            "seed": result.seed,
            "scenario_count": result.scenario_count,
            "success_rate": result.success_rate,
            "insolvency_years": result.insolvency_years,
            "annual": [asdict(row) for row in result.annual],
        }
    )

    plan_hash = hashlib.sha256(Path(plan_path).read_bytes()).hexdigest()[:12]
    title = f"TFP Report - {html.escape(plan.people.primary.name)}"
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title}</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 1.5rem; color: #111827; }}
    h1 {{ margin-bottom: 0.25rem; }}
    .meta {{ color: #4b5563; margin-bottom: 1rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #d1d5db; padding: 0.45rem 0.55rem; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    .warn {{ color: #b91c1c; font-weight: 600; }}
    pre {{ background: #f3f4f6; padding: 0.75rem; overflow-x: auto; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class=\"meta\">Mode: {html.escape(result.mode)} | Seed: {result.seed} | Generated: {timestamp} | Plan hash: {plan_hash}</div>
  <h2>Annual Summary</h2>
  <table>
    <thead>
      <tr><th>Year</th><th>Income</th><th>Expenses</th><th>Net Flow</th><th>Net Worth End</th></tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <p class=\"warn\">This is an initial implementation scaffold; full simulation semantics and charts are pending.</p>
  <h2>Embedded Data</h2>
  <pre id=\"payload\"></pre>
  <script>
    const data = {payload};
    document.getElementById('payload').textContent = JSON.stringify(data, null, 2);
  </script>
</body>
</html>
"""


def write_report(path: str | Path, html_content: str) -> None:
    Path(path).write_text(html_content, encoding="utf-8")
