"""CLI entry point for TFP."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .report import render_report, write_report
from .schema import SchemaError, load_plan
from .simulation import run_simulation
from .validate import validate_plan


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Timmy's Financial Planner")
    parser.add_argument("plan", help="Path to plan JSON file")
    parser.add_argument("-o", "--output", default="report.html", help="Output HTML path")
    parser.add_argument("--mode", choices=["deterministic", "monte_carlo", "historical"], help="Override simulation mode")
    parser.add_argument("--runs", type=int, help="Override Monte Carlo run count")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--validate", action="store_true", help="Validate JSON only")
    parser.add_argument("--summary", action="store_true", help="Print text summary to stdout")
    return parser


def _print_validation(errors: list[str], warnings: list[str]) -> None:
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        plan = load_plan(args.plan)
    except (SchemaError, OSError, ValueError) as exc:
        print(f"Failed to load plan: {exc}", file=sys.stderr)
        return 2

    validation = validate_plan(plan)
    _print_validation(validation.errors, validation.warnings)
    if not validation.is_valid:
        return 1

    if args.validate:
        print("Plan is valid.")
        return 0

    result = run_simulation(plan, mode_override=args.mode, runs_override=args.runs, seed=args.seed)
    html_content = render_report(plan, result, plan_path=args.plan)
    write_report(args.output, html_content)

    if args.summary and result.annual:
        first = result.annual[0]
        last = result.annual[-1]
        print(f"Mode: {result.mode}")
        print(f"Years: {first.year}-{last.year}")
        print(f"Ending net worth: ${last.net_worth_end:,.0f}")
        print(f"Insolvency years: {len(result.insolvency_years)}")

    print(f"Wrote report to {Path(args.output)}")
    if result.seed is not None:
        print(f"Seed: {result.seed}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
