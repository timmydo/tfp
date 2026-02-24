"""HTML template assets for report rendering."""

from __future__ import annotations


def render_html_document(
    *,
    title: str,
    subtitle: str,
    overview_panel: str,
    annual_table: str,
    account_tables: str,
    account_balance_table: str,
    account_flow_table: str,
    tax_table: str,
    calc_log_table: str,
    validation_table: str,
) -> str:
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #f4efe8;
      --panel: #fffdf8;
      --ink: #1f2937;
      --muted: #6b7280;
      --line: #d7c7af;
      --brand: #9a3412;
      --warn: #991b1b;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: 'Trebuchet MS', 'Segoe UI', sans-serif; color: var(--ink); background: radial-gradient(circle at top right, #f9d8b4 0, var(--bg) 45%); }}
    .wrap {{ max-width: 1280px; margin: 0 auto; padding: 1rem; }}
    h1 {{ margin: 0.1rem 0 0.25rem; font-size: 1.9rem; }}
    .meta {{ color: var(--muted); font-size: 0.95rem; margin-bottom: 0.8rem; }}
    .tabs {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.75rem 0; }}
    .tab-btn {{ border: 1px solid var(--line); background: #fff; padding: 0.45rem 0.75rem; cursor: pointer; border-radius: 999px; font-weight: 700; }}
    .tab-btn.active {{ background: var(--brand); color: #fff; border-color: var(--brand); }}
    .tab {{ display: none; }}
    .tab.active {{ display: block; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 0.85rem; margin-bottom: 0.85rem; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
    th, td {{ border: 1px solid #e9dbc7; padding: 0.35rem 0.45rem; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    .table-wrap {{ width: 100%; max-width: 100%; overflow-x: auto; }}
    .calc-log table {{ table-layout: fixed; }}
    .calc-log th, .calc-log td {{ padding: 0.25rem 0.3rem; font-size: 0.78rem; white-space: normal; overflow-wrap: anywhere; }}
    .cell-main {{ font-weight: 700; }}
    .cell-breakdown {{ margin-top: 0.25rem; font-size: 0.76rem; color: var(--muted); line-height: 1.3; text-align: left; white-space: normal; }}
    .insolvent {{ background: #ffe3e3; color: var(--warn); font-weight: 700; }}
    .subtle {{ color: var(--muted); font-size: 0.85rem; }}
    details {{ margin-top: 0.75rem; }}
    summary {{ cursor: pointer; }}
    pre {{ margin: 0.5rem 0 0; padding: 0.6rem; background: #fff; border: 1px solid #e9dbc7; border-radius: 8px; overflow-x: auto; font-size: 0.78rem; line-height: 1.3; }}
    @media (max-width: 700px) {{
      h1 {{ font-size: 1.5rem; }}
      .tab-btn {{ font-size: 0.9rem; }}
    }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>{title}</h1>
    <div class=\"meta\">{subtitle}</div>
    <div class=\"tabs\" id=\"tabs\">
      <button class=\"tab-btn active\" data-tab=\"overview\">Overview</button>
      <button class=\"tab-btn\" data-tab=\"flows\">Annual Financials</button>
      <button class=\"tab-btn\" data-tab=\"accounts\">Account Details</button>
      <button class=\"tab-btn\" data-tab=\"account-balances\">Account Balance View</button>
      <button class=\"tab-btn\" data-tab=\"account-flows\">Account Activity View</button>
      <button class=\"tab-btn\" data-tab=\"taxes\">Taxes</button>
      <button class=\"tab-btn\" data-tab=\"calc-log\">Calculation Log</button>
      <button class=\"tab-btn\" data-tab=\"validation\">Plan Validation</button>
    </div>

    <section class=\"tab active\" id=\"tab-overview\">
      <div class=\"panel\">{overview_panel}</div>
    </section>

    <section class=\"tab\" id=\"tab-flows\">
      <div class=\"panel\">
        <h3>Annual Financials</h3>
        <p class=\"subtle\">Consolidated yearly totals with in-table breakdowns for expenses, taxes, withdrawals, contributions, transfers, and net worth.</p>
        {annual_table}
      </div>
    </section>

    <section class=\"tab\" id=\"tab-accounts\">
      <div class=\"panel\">{account_tables}</div>
    </section>

    <section class=\"tab\" id=\"tab-account-balances\">
      <div class=\"panel\">
        <h3>Monthly Account Balances</h3>
        <p class=\"subtle\">End-of-month balances for each account.</p>
        {account_balance_table}
      </div>
    </section>

    <section class=\"tab\" id=\"tab-account-flows\">
      <div class=\"panel\">
        <h3>Monthly Account Activity</h3>
        <p class=\"subtle\">Month-over-month change in each account balance (positive = added, negative = removed), with per-cell breakdown details shown inline.</p>
        {account_flow_table}
      </div>
    </section>

    <section class=\"tab\" id=\"tab-taxes\">
      <div class=\"panel\">
        <h3>Monthly Taxes</h3>
        <p class=\"subtle\">Month-by-month tax cash flows. Hover cells for breakdowns and projection basis used for estimated payments.</p>
        {tax_table}
      </div>
    </section>

    <section class=\"tab\" id=\"tab-calc-log\">
      <div class=\"panel\">
        <h3>Monthly Calculation Log</h3>
        <p class=\"subtle\">Verbose monthly ledger of computed amounts used by the deterministic engine. Hover numeric cells for why they were calculated.</p>
        {calc_log_table}
      </div>
    </section>

    <section class=\"tab\" id=\"tab-validation\">
      <div class=\"panel\">
        <h3>Plan Validation and Common Mistakes</h3>
        <p class=\"subtle\">Schema validation warnings plus non-blocking sanity checks for unusual assumptions.</p>
        {validation_table}
      </div>
    </section>
  </div>

  <script>
    function tabsInit() {{
      const buttons = [...document.querySelectorAll('.tab-btn')];
      buttons.forEach((btn) => {{
        btn.addEventListener('click', () => {{
          buttons.forEach((b) => b.classList.remove('active'));
          btn.classList.add('active');
          [...document.querySelectorAll('.tab')].forEach((tab) => tab.classList.remove('active'));
          document.getElementById(`tab-${{btn.dataset.tab}}`).classList.add('active');
        }});
      }});
    }}

    tabsInit();
  </script>
</body>
</html>
"""
