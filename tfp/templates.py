"""HTML template assets for report rendering."""

from __future__ import annotations


def render_html_document(*, title: str, subtitle: str, dashboard_cards: str, annual_table: str, flow_table: str, account_tables: str, payload_json: str) -> str:
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
    .grid {{ display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}
    .cards {{ display: grid; gap: 0.6rem; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }}
    .card {{ background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: 0.65rem; }}
    .card .k {{ color: var(--muted); font-size: 0.85rem; }}
    .card .v {{ font-size: 1.2rem; font-weight: 700; }}
    canvas {{ width: 100%; height: 260px; display: block; background: #fff; border: 1px solid #eadfce; border-radius: 10px; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
    th, td {{ border: 1px solid #e9dbc7; padding: 0.35rem 0.45rem; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    .insolvent {{ background: #ffe3e3; color: var(--warn); font-weight: 700; }}
    .subtle {{ color: var(--muted); font-size: 0.85rem; }}
    input[type=range] {{ width: 100%; }}
    @media (max-width: 700px) {{
      h1 {{ font-size: 1.5rem; }}
      .tab-btn {{ font-size: 0.9rem; }}
      canvas {{ height: 220px; }}
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
    </div>

    <section class=\"tab active\" id=\"tab-dashboard\">
      <div class=\"cards\">{dashboard_cards}</div>
      <div class=\"panel\"><canvas id=\"chart-net-worth\"></canvas></div>
      <div class=\"grid\">
        <div class=\"panel\"><canvas id=\"chart-income-expenses\"></canvas></div>
        <div class=\"panel\"><canvas id=\"chart-success\"></canvas></div>
      </div>
    </section>

    <section class=\"tab\" id=\"tab-charts\">
      <div class=\"grid\">
        <div class=\"panel\"><canvas id=\"chart-accounts-stack\"></canvas></div>
        <div class=\"panel\"><canvas id=\"chart-account-lines\"></canvas></div>
        <div class=\"panel\"><canvas id=\"chart-tax\"></canvas></div>
        <div class=\"panel\"><canvas id=\"chart-allocation\"></canvas></div>
        <div class=\"panel\"><canvas id=\"chart-withdrawals\"></canvas></div>
      </div>
    </section>

    <section class=\"tab\" id=\"tab-flows\">
      <div class=\"panel\">
        <label for=\"sankey-year\">Year: <strong id=\"sankey-year-label\"></strong></label>
        <input id=\"sankey-year\" type=\"range\" min=\"0\" max=\"0\" value=\"0\" />
      </div>
      <div class=\"panel\"><canvas id=\"chart-sankey\"></canvas></div>
      <div class=\"panel\">{flow_table}</div>
    </section>

    <section class=\"tab\" id=\"tab-tables\">
      <div class=\"panel\">{annual_table}</div>
    </section>

    <section class=\"tab\" id=\"tab-accounts\">
      <div class=\"panel\">{account_tables}</div>
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

    function drawAxes(ctx, w, h) {{
      ctx.strokeStyle = '#ddd';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(40, 10); ctx.lineTo(40, h - 24); ctx.lineTo(w - 8, h - 24); ctx.stroke();
    }}

    function drawLine(canvasId, years, series, title, color) {{
      const c = document.getElementById(canvasId); if (!c) return;
      const rect = c.getBoundingClientRect(); c.width = Math.max(380, Math.floor(rect.width)); c.height = Math.floor(rect.height);
      const ctx = c.getContext('2d'); const w = c.width, h = c.height;
      ctx.clearRect(0, 0, w, h); drawAxes(ctx, w, h);
      const vals = series.map(Number); const maxV = Math.max(1, ...vals);
      const minV = Math.min(0, ...vals); const span = Math.max(1, maxV - minV);
      ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.beginPath();
      vals.forEach((v, i) => {{
        const x = 40 + (i * (w - 56) / Math.max(1, vals.length - 1));
        const y = (h - 24) - ((v - minV) / span) * (h - 38);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }});
      ctx.stroke();
      ctx.fillStyle = '#111'; ctx.font = 'bold 12px sans-serif'; ctx.fillText(title, 46, 22);
      ctx.fillStyle = '#666'; ctx.font = '11px sans-serif';
      ctx.fillText(String(years[0] ?? ''), 40, h - 8);
      ctx.fillText(String(years[years.length - 1] ?? ''), w - 40, h - 8);
      ctx.fillText(fmtMoney(maxV), 4, 20);
    }}

    function drawBars(canvasId, years, stacks, title) {{
      const c = document.getElementById(canvasId); if (!c) return;
      const rect = c.getBoundingClientRect(); c.width = Math.max(380, Math.floor(rect.width)); c.height = Math.floor(rect.height);
      const ctx = c.getContext('2d'); const w = c.width, h = c.height;
      ctx.clearRect(0, 0, w, h); drawAxes(ctx, w, h);
      const names = Object.keys(stacks);
      const palette = ['#9a3412','#166534','#1d4ed8','#92400e','#6b21a8','#be123c','#0f766e'];
      const totals = years.map((_, i) => names.reduce((sum, n) => sum + Number((stacks[n] || [])[i] || 0), 0));
      const maxV = Math.max(1, ...totals);
      years.forEach((_, i) => {{
        const x = 44 + i * (w - 58) / Math.max(1, years.length);
        const bw = Math.max(2, (w - 70) / Math.max(1, years.length) - 1);
        let top = h - 24;
        names.forEach((name, idx) => {{
          const v = Number((stacks[name] || [])[i] || 0);
          if (v <= 0) return;
          const bh = (v / maxV) * (h - 38);
          ctx.fillStyle = palette[idx % palette.length];
          ctx.fillRect(x, top - bh, bw, bh);
          top -= bh;
        }});
      }});
      ctx.fillStyle = '#111'; ctx.font = 'bold 12px sans-serif'; ctx.fillText(title, 46, 22);
    }}

    function drawAreaStack(canvasId, years, stacks, title) {{
      const c = document.getElementById(canvasId); if (!c) return;
      const rect = c.getBoundingClientRect(); c.width = Math.max(380, Math.floor(rect.width)); c.height = Math.floor(rect.height);
      const ctx = c.getContext('2d'); const w = c.width, h = c.height;
      ctx.clearRect(0, 0, w, h); drawAxes(ctx, w, h);
      const names = Object.keys(stacks);
      const palette = ['#f97316','#16a34a','#2563eb','#7c3aed','#db2777','#0891b2'];
      const totals = years.map((_, i) => names.reduce((sum, n) => sum + Number((stacks[n] || [])[i] || 0), 0));
      const maxV = Math.max(1, ...totals);
      const cumulative = years.map(() => 0);
      names.forEach((name, idx) => {{
        ctx.beginPath();
        years.forEach((_, i) => {{
          const x = 40 + i * (w - 56) / Math.max(1, years.length - 1);
          const next = cumulative[i] + Number((stacks[name] || [])[i] || 0);
          const y = (h - 24) - (next / maxV) * (h - 38);
          if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          cumulative[i] = next;
        }});
        for (let i = years.length - 1; i >= 0; i--) {{
          const x = 40 + i * (w - 56) / Math.max(1, years.length - 1);
          const prev = cumulative[i] - Number((stacks[name] || [])[i] || 0);
          const y = (h - 24) - (prev / maxV) * (h - 38);
          ctx.lineTo(x, y);
        }}
        ctx.closePath();
        ctx.fillStyle = palette[idx % palette.length] + 'aa';
        ctx.fill();
      }});
      ctx.fillStyle = '#111'; ctx.font = 'bold 12px sans-serif'; ctx.fillText(title, 46, 22);
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
      const sx = 32, dx = w - 180;
      let y1 = 20, y2 = 20;
      const srcNodes = src.map(([k,v]) => {{ const hh = Math.max(16, (Number(v)/srcTotal)*(h-40)); const n = {{k,v:Number(v),x:sx,y:y1,h:hh}}; y1 += hh + 6; return n; }});
      const dstNodes = dst.map(([k,v]) => {{ const hh = Math.max(16, (Number(v)/dstTotal)*(h-40)); const n = {{k,v:Number(v),x:dx,y:y2,h:hh}}; y2 += hh + 6; return n; }});
      ctx.font = '11px sans-serif';
      srcNodes.forEach((n) => {{ ctx.fillStyle = '#bfdbfe'; ctx.fillRect(n.x, n.y, 140, n.h); ctx.fillStyle = '#1f2937'; ctx.fillText(`${{n.k}}  ${{Math.round(n.v).toLocaleString()}}`, n.x+4, n.y+12); }});
      dstNodes.forEach((n) => {{ ctx.fillStyle = '#fecaca'; ctx.fillRect(n.x, n.y, 140, n.h); ctx.fillStyle = '#1f2937'; ctx.fillText(`${{n.k}}  ${{Math.round(n.v).toLocaleString()}}`, n.x+4, n.y+12); }});
      srcNodes.forEach((s, si) => {{
        dstNodes.forEach((d, di) => {{
          const width = Math.max(1, ((s.v/srcTotal) * (d.v/dstTotal)) * 18);
          ctx.strokeStyle = `rgba(120,120,120,${{Math.min(0.35, 0.08 + width/40)}})`;
          ctx.lineWidth = width;
          ctx.beginPath();
          ctx.moveTo(s.x + 140, s.y + s.h/2);
          ctx.bezierCurveTo(w*0.42, s.y + s.h/2, w*0.58, d.y + d.h/2, d.x, d.y + d.h/2);
          ctx.stroke();
        }});
      }});
      ctx.fillStyle = '#111'; ctx.font = 'bold 12px sans-serif'; ctx.fillText('Money Flow', 10, 12);
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
        drawLine('chart-success', years, payload.charts.success.p50, `Success / Median (rate ${{(payload.charts.success.rate||0)*100}}% )`, '#6b21a8');
      }} else {{
        drawLine('chart-success', years, payload.charts.netWorth, `Success Rate ${{(payload.charts.success.rate||0)*100}}%`, '#6b21a8');
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
