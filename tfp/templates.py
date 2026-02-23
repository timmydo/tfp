"""HTML template assets for report rendering."""

from __future__ import annotations


def render_html_document(
    *,
    title: str,
    subtitle: str,
    dashboard_cards: str,
    annual_table: str,
    flow_table: str,
    account_tables: str,
    calc_log_table: str,
    validation_table: str,
    payload_json: str,
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
      --ok: #166534;
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
    .cards {{ display: grid; gap: 0.6rem; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }}
    .card {{ background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: 0.65rem; }}
    .card .k {{ color: var(--muted); font-size: 0.85rem; }}
    .card .v {{ font-size: 1.2rem; font-weight: 700; }}
    .chart-title {{ margin: 0 0 0.15rem; font-size: 1.1rem; font-weight: 700; color: var(--ink); }}
    .chart-desc {{ margin: 0 0 0.5rem; font-size: 0.88rem; color: var(--muted); }}
    canvas {{ width: 100%; height: 450px; display: block; background: #fff; border: 1px solid #eadfce; border-radius: 10px; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
    th, td {{ border: 1px solid #e9dbc7; padding: 0.35rem 0.45rem; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    .insolvent {{ background: #ffe3e3; color: var(--warn); font-weight: 700; }}
    .subtle {{ color: var(--muted); font-size: 0.85rem; }}
    input[type=range] {{ width: 100%; }}
    @media (max-width: 700px) {{
      h1 {{ font-size: 1.5rem; }}
      .tab-btn {{ font-size: 0.9rem; }}
      canvas {{ height: 320px; }}
    }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>{title}</h1>
    <div class=\"meta\">{subtitle}</div>
    <div class=\"tabs\" id=\"tabs\">
      <button class=\"tab-btn active\" data-tab=\"dashboard\">Dashboard</button>
      <button class=\"tab-btn\" data-tab=\"charts\">Charts</button>
      <button class=\"tab-btn\" data-tab=\"flows\">Money Flows</button>
      <button class=\"tab-btn\" data-tab=\"tables\">Tables</button>
      <button class=\"tab-btn\" data-tab=\"accounts\">Account Details</button>
      <button class=\"tab-btn\" data-tab=\"calc-log\">Calculation Log</button>
      <button class=\"tab-btn\" data-tab=\"validation\">Plan Validation</button>
    </div>

    <section class=\"tab active\" id=\"tab-dashboard\">
      <div class=\"cards\">{dashboard_cards}</div>
      <div class=\"panel\">
        <h3 class=\"chart-title\">Net Worth Over Time</h3>
        <p class=\"chart-desc\">Total net worth across all accounts projected over the plan period.</p>
        <canvas id=\"chart-net-worth\"></canvas>
      </div>
      <div class=\"panel\">
        <h3 class=\"chart-title\">Income vs Expenses</h3>
        <p class=\"chart-desc\">Net difference between total income and total expenses each year.</p>
        <canvas id=\"chart-income-expenses\"></canvas>
      </div>
      <div class=\"panel\">
        <h3 class=\"chart-title\" id=\"chart-success-title\">Probability of Success</h3>
        <p class=\"chart-desc\" id=\"chart-success-desc\">Median portfolio value across simulations with success rate.</p>
        <canvas id=\"chart-success\"></canvas>
      </div>
    </section>

    <section class=\"tab\" id=\"tab-charts\">
      <div class=\"panel\">
        <h3 class=\"chart-title\">Net Worth by Account</h3>
        <p class=\"chart-desc\">Stacked breakdown of net worth by individual account.</p>
        <canvas id=\"chart-accounts-stack\"></canvas>
      </div>
      <div class=\"panel\">
        <h3 class=\"chart-title\">Total Balance Trend</h3>
        <p class=\"chart-desc\">Overall portfolio balance trajectory over the plan period.</p>
        <canvas id=\"chart-account-lines\"></canvas>
      </div>
      <div class=\"panel\">
        <h3 class=\"chart-title\">Tax Burden</h3>
        <p class=\"chart-desc\">Annual tax breakdown by category: federal, state, capital gains, NIIT, AMT, and penalties.</p>
        <canvas id=\"chart-tax\"></canvas>
      </div>
      <div class=\"panel\">
        <h3 class=\"chart-title\">Asset Allocation</h3>
        <p class=\"chart-desc\">Portfolio mix of stocks, bonds, and cash across all accounts over time.</p>
        <canvas id=\"chart-allocation\"></canvas>
      </div>
      <div class=\"panel\">
        <h3 class=\"chart-title\">Withdrawal Sources</h3>
        <p class=\"chart-desc\">Which accounts are drawn from each year to cover expenses.</p>
        <canvas id=\"chart-withdrawals\"></canvas>
      </div>
    </section>

    <section class=\"tab\" id=\"tab-flows\">
      <div class=\"panel\">
        <label for=\"sankey-year\">Year: <strong id=\"sankey-year-label\"></strong></label>
        <input id=\"sankey-year\" type=\"range\" min=\"0\" max=\"0\" value=\"0\" />
      </div>
      <div class=\"panel\">
        <h3 class=\"chart-title\">Money Flow</h3>
        <p class=\"chart-desc\">Sankey diagram showing how money flows from income sources to expense categories.</p>
        <canvas id=\"chart-sankey\"></canvas>
      </div>
      <div class=\"panel\">{flow_table}</div>
    </section>

    <section class=\"tab\" id=\"tab-tables\">
      <div class=\"panel\">{annual_table}</div>
    </section>

    <section class=\"tab\" id=\"tab-accounts\">
      <div class=\"panel\">{account_tables}</div>
    </section>

    <section class=\"tab\" id=\"tab-calc-log\">
      <div class=\"panel\">
        <h3 class=\"chart-title\">Monthly Calculation Log</h3>
        <p class=\"chart-desc\">Verbose monthly ledger of computed amounts used by the deterministic engine.</p>
        {calc_log_table}
      </div>
    </section>

    <section class=\"tab\" id=\"tab-validation\">
      <div class=\"panel\">
        <h3 class=\"chart-title\">Plan Validation and Common Mistakes</h3>
        <p class=\"chart-desc\">Schema validation warnings plus non-blocking sanity checks for unusual assumptions.</p>
        {validation_table}
      </div>
    </section>
  </div>

  <script>
    const payload = {payload_json};

    function fmtMoney(v) {{
      return '$' + (Number(v || 0)).toLocaleString(undefined, {{ maximumFractionDigits: 0 }});
    }}

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

    const M = {{ left: 70, right: 20, top: 20, bottom: 40 }};

    function drawAxes(ctx, w, h, years, maxV, minV) {{
      const plotH = h - M.top - M.bottom;
      const plotW = w - M.left - M.right;
      ctx.strokeStyle = '#ccc';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(M.left, M.top);
      ctx.lineTo(M.left, h - M.bottom);
      ctx.lineTo(w - M.right, h - M.bottom);
      ctx.stroke();

      const span = Math.max(1, (maxV || 1) - (minV || 0));
      const gridLines = 5;
      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = '#e0e0e0';
      ctx.lineWidth = 1;
      ctx.fillStyle = '#666';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'right';
      for (let i = 0; i <= gridLines; i++) {{
        const frac = i / gridLines;
        const yVal = (minV || 0) + frac * span;
        const yPx = h - M.bottom - frac * plotH;
        if (i > 0 && i < gridLines) {{
          ctx.beginPath();
          ctx.moveTo(M.left, yPx);
          ctx.lineTo(w - M.right, yPx);
          ctx.stroke();
        }}
        ctx.fillText(fmtMoney(yVal), M.left - 6, yPx + 4);
      }}
      ctx.setLineDash([]);

      if (years && years.length > 0) {{
        ctx.textAlign = 'center';
        ctx.fillStyle = '#666';
        ctx.font = '12px sans-serif';
        const step = Math.max(1, Math.ceil(years.length / 10));
        for (let i = 0; i < years.length; i += step) {{
          const x = M.left + (i / Math.max(1, years.length - 1)) * plotW;
          ctx.fillText(String(years[i]), x, h - M.bottom + 16);
        }}
        if ((years.length - 1) % step !== 0) {{
          const x = M.left + plotW;
          ctx.fillText(String(years[years.length - 1]), x, h - M.bottom + 16);
        }}
      }}
      ctx.textAlign = 'left';
    }}

    function drawLegend(ctx, names, palette, x, y) {{
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'left';
      let cx = x;
      names.forEach((name, i) => {{
        ctx.fillStyle = palette[i % palette.length];
        ctx.fillRect(cx, y - 10, 12, 12);
        ctx.fillStyle = '#333';
        const label = name.length > 18 ? name.slice(0, 16) + '..' : name;
        ctx.fillText(label, cx + 16, y);
        cx += ctx.measureText(label).width + 32;
        if (cx > ctx.canvas.width - M.right - 40) {{
          cx = x;
          y += 18;
        }}
      }});
    }}

    function drawLine(canvasId, years, series, title, color) {{
      const c = document.getElementById(canvasId); if (!c) return;
      const rect = c.getBoundingClientRect(); c.width = Math.max(380, Math.floor(rect.width)); c.height = Math.floor(rect.height);
      const ctx = c.getContext('2d'); const w = c.width, h = c.height;
      ctx.clearRect(0, 0, w, h);
      const vals = series.map(Number); const maxV = Math.max(1, ...vals);
      const minV = Math.min(0, ...vals); const span = Math.max(1, maxV - minV);
      drawAxes(ctx, w, h, years, maxV, minV);
      const plotW = w - M.left - M.right;
      const plotH = h - M.top - M.bottom;
      ctx.strokeStyle = color; ctx.lineWidth = 2.5; ctx.beginPath();
      vals.forEach((v, i) => {{
        const x = M.left + (i * plotW / Math.max(1, vals.length - 1));
        const y = (h - M.bottom) - ((v - minV) / span) * plotH;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }});
      ctx.stroke();
    }}

    function drawBars(canvasId, years, stacks, title) {{
      const c = document.getElementById(canvasId); if (!c) return;
      const rect = c.getBoundingClientRect(); c.width = Math.max(380, Math.floor(rect.width)); c.height = Math.floor(rect.height);
      const ctx = c.getContext('2d'); const w = c.width, h = c.height;
      ctx.clearRect(0, 0, w, h);
      const names = Object.keys(stacks);
      const palette = ['#9a3412','#166534','#1d4ed8','#92400e','#6b21a8','#be123c','#0f766e'];
      const totals = years.map((_, i) => names.reduce((sum, n) => sum + Number((stacks[n] || [])[i] || 0), 0));
      const maxV = Math.max(1, ...totals);
      drawAxes(ctx, w, h, years, maxV, 0);
      const plotW = w - M.left - M.right;
      const plotH = h - M.top - M.bottom;
      years.forEach((_, i) => {{
        const x = M.left + 4 + i * plotW / Math.max(1, years.length);
        const bw = Math.max(2, plotW / Math.max(1, years.length) - 2);
        let top = h - M.bottom;
        names.forEach((name, idx) => {{
          const v = Number((stacks[name] || [])[i] || 0);
          if (v <= 0) return;
          const bh = (v / maxV) * plotH;
          ctx.fillStyle = palette[idx % palette.length];
          ctx.fillRect(x, top - bh, bw, bh);
          top -= bh;
        }});
      }});
      drawLegend(ctx, names, palette, M.left + 4, M.top + 14);
    }}

    function drawAreaStack(canvasId, years, stacks, title) {{
      const c = document.getElementById(canvasId); if (!c) return;
      const rect = c.getBoundingClientRect(); c.width = Math.max(380, Math.floor(rect.width)); c.height = Math.floor(rect.height);
      const ctx = c.getContext('2d'); const w = c.width, h = c.height;
      ctx.clearRect(0, 0, w, h);
      const names = Object.keys(stacks);
      const palette = ['#f97316','#16a34a','#2563eb','#7c3aed','#db2777','#0891b2'];
      const totals = years.map((_, i) => names.reduce((sum, n) => sum + Number((stacks[n] || [])[i] || 0), 0));
      const maxV = Math.max(1, ...totals);
      drawAxes(ctx, w, h, years, maxV, 0);
      const plotW = w - M.left - M.right;
      const plotH = h - M.top - M.bottom;
      const cumulative = years.map(() => 0);
      names.forEach((name, idx) => {{
        ctx.beginPath();
        years.forEach((_, i) => {{
          const x = M.left + i * plotW / Math.max(1, years.length - 1);
          const next = cumulative[i] + Number((stacks[name] || [])[i] || 0);
          const y = (h - M.bottom) - (next / maxV) * plotH;
          if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          cumulative[i] = next;
        }});
        for (let i = years.length - 1; i >= 0; i--) {{
          const x = M.left + i * plotW / Math.max(1, years.length - 1);
          const prev = cumulative[i] - Number((stacks[name] || [])[i] || 0);
          const y = (h - M.bottom) - (prev / maxV) * plotH;
          ctx.lineTo(x, y);
        }}
        ctx.closePath();
        ctx.fillStyle = palette[idx % palette.length] + 'cc';
        ctx.fill();
      }});
      drawLegend(ctx, names, palette, M.left + 4, M.top + 14);
    }}

    function renderSankey(yearIndex) {{
      const years = payload.sankey.years;
      const year = years[yearIndex] || years[0];
      const flow = payload.sankey.flows[year] || {{ sources: {{}}, destinations: {{}} }};
      document.getElementById('sankey-year-label').textContent = String(year || '');
      const c = document.getElementById('chart-sankey');
      const rect = c.getBoundingClientRect(); c.width = Math.max(380, Math.floor(rect.width)); c.height = Math.floor(rect.height);
      const ctx = c.getContext('2d'); const w = c.width, h = c.height;
      ctx.clearRect(0, 0, w, h);
      const src = Object.entries(flow.sources || {{}}).filter(([,v]) => Number(v) > 0);
      const dst = Object.entries(flow.destinations || {{}}).filter(([,v]) => Number(v) > 0);
      const srcTotal = src.reduce((s, [,v]) => s + Number(v), 0) || 1;
      const dstTotal = dst.reduce((s, [,v]) => s + Number(v), 0) || 1;
      const sx = 32, dx = w - 200;
      let y1 = 20, y2 = 20;
      const srcNodes = src.map(([k,v]) => {{ const hh = Math.max(18, (Number(v)/srcTotal)*(h-40)); const n = {{k,v:Number(v),x:sx,y:y1,h:hh}}; y1 += hh + 8; return n; }});
      const dstNodes = dst.map(([k,v]) => {{ const hh = Math.max(18, (Number(v)/dstTotal)*(h-40)); const n = {{k,v:Number(v),x:dx,y:y2,h:hh}}; y2 += hh + 8; return n; }});
      ctx.font = '13px sans-serif';
      srcNodes.forEach((n) => {{ ctx.fillStyle = '#bfdbfe'; ctx.fillRect(n.x, n.y, 160, n.h); ctx.fillStyle = '#1f2937'; ctx.fillText(`${{n.k}}  ${{Math.round(n.v).toLocaleString()}}`, n.x+6, n.y+14); }});
      dstNodes.forEach((n) => {{ ctx.fillStyle = '#fecaca'; ctx.fillRect(n.x, n.y, 160, n.h); ctx.fillStyle = '#1f2937'; ctx.fillText(`${{n.k}}  ${{Math.round(n.v).toLocaleString()}}`, n.x+6, n.y+14); }});
      srcNodes.forEach((s, si) => {{
        dstNodes.forEach((d, di) => {{
          const width = Math.max(1, ((s.v/srcTotal) * (d.v/dstTotal)) * 18);
          ctx.strokeStyle = `rgba(120,120,120,${{Math.min(0.35, 0.08 + width/40)}})`;
          ctx.lineWidth = width;
          ctx.beginPath();
          ctx.moveTo(s.x + 160, s.y + s.h/2);
          ctx.bezierCurveTo(w*0.42, s.y + s.h/2, w*0.58, d.y + d.h/2, d.x, d.y + d.h/2);
          ctx.stroke();
        }});
      }});
    }}

    function renderAll() {{
      const years = payload.charts.years;
      drawLine('chart-net-worth', years, payload.charts.netWorth, 'Net Worth', '#9a3412');
      drawLine('chart-income-expenses', years, payload.charts.income.map((v,i)=>v-payload.charts.expenses[i]), 'Income - Expenses', '#166534');
      drawAreaStack('chart-accounts-stack', years, payload.charts.accountsStacked, 'Net Worth by Account');
      drawLine('chart-account-lines', years, payload.charts.netWorth, 'Total Balance Trend', '#1d4ed8');
      drawBars('chart-tax', years, payload.charts.taxBurden, 'Tax Burden');
      drawAreaStack('chart-allocation', years, payload.charts.allocation, 'Asset Allocation');
      drawBars('chart-withdrawals', years, payload.charts.withdrawalSources, 'Withdrawal Sources');
      if ((payload.charts.success.p50 || []).length > 0) {{
        const titleEl = document.getElementById('chart-success-title');
        const descEl = document.getElementById('chart-success-desc');
        if (titleEl) titleEl.textContent = 'Probability of Success';
        if (descEl) descEl.textContent = 'Median portfolio value across simulations with success rate.';
        drawLine('chart-success', years, payload.charts.success.p50, `Success / Median (rate ${{(payload.charts.success.rate||0)*100}}% )`, '#6b21a8');
      }} else {{
        const titleEl = document.getElementById('chart-success-title');
        const descEl = document.getElementById('chart-success-desc');
        if (titleEl) titleEl.textContent = 'Net Worth Trend';
        if (descEl) descEl.textContent = 'Total portfolio balance trend over time.';
        drawLine('chart-success', years, payload.charts.netWorth, `Net Worth Trend`, '#6b21a8');
      }}

      const slider = document.getElementById('sankey-year');
      slider.max = String(Math.max(0, payload.sankey.years.length - 1));
      slider.value = '0';
      slider.addEventListener('input', () => renderSankey(Number(slider.value || 0)));
      renderSankey(0);
    }}

    tabsInit();
    renderAll();
    addEventListener('resize', () => renderAll());
  </script>
</body>
</html>
"""
