# TFP - Timmy's Financial Planner

TFP is a command-line Python app that reads a `plan.json` financial plan and generates a self-contained `report.html`.

This workflow is designed for collaborating with an AI agent:

1. You and the AI agent edit `plan.json`.
2. TFP regenerates `report.html`.
3. You refresh the browser to see updates.

## Quick Start

1. Ensure Python 3.10+ is installed.
2. From the repo root, run:

```bash
python3 -m tfp plan.json --server
```

By default this:
- Writes/updates `report.html`
- Serves it at `http://127.0.0.1:8000/report.html`
- Watches `plan.json` for changes and regenerates the report automatically

## Working With an AI Agent

Use this loop:

1. Ask the AI agent to update `plan.json` (accounts, income, expenses, taxes, assumptions, etc.).
2. Save the file.
3. TFP detects the change and rebuilds the report.
4. Refresh your browser to review the updated charts/tables.
5. Repeat until the plan looks right.

Example prompts for the AI agent:
- "Increase annual salary to 180000 and extend retirement date to 2040-06."
- "Add a Roth conversion of 40000/year from 2030-01 to 2037-12."
- "Lower inflation to 2.5% and rerun assumptions."

## Recommended Command Options

```bash
python3 -m tfp plan.json --server --mode deterministic --port 8000 --watch-interval 0.5
```

Useful flags:
- `-o, --output`: output HTML filename/path (default: `report.html`)
- `--host`: server bind host (default: `127.0.0.1`)
- `--port`: server port (default: `8000`)
- `--watch-interval`: polling interval in seconds (default: `1.0`)
- `--mode`: override simulation mode (`deterministic`, `monte_carlo`, `historical`)

## Validation and One-Off Runs

Validate only:

```bash
python3 -m tfp plan.json --validate
```

Generate once without server mode:

```bash
python3 -m tfp plan.json -o report.html
```

## Troubleshooting

- If startup fails with validation errors, fix the reported JSON paths in `plan.json` and rerun.
- If `--server` is running but the browser is stale, refresh the page.
- If the port is in use, pick another one (for example `--port 8001`).
