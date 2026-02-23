"""CLI entry point for TFP."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading

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
    parser.add_argument("--server", action="store_true", help="Watch plan file, regenerate output, and serve via local web server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind local web server (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port for local web server (default: 8000)")
    parser.add_argument("--watch-interval", type=float, default=1.0, help="Plan file watch interval in seconds (default: 1.0)")
    return parser


def _print_validation(errors: list[str], warnings: list[str]) -> None:
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)


def _write_report_for_plan(plan: dict, args: argparse.Namespace, *, print_header: bool = True) -> None:
    result = run_simulation(plan, mode_override=args.mode, runs_override=args.runs, seed=args.seed)
    html_content = render_report(plan, result, plan_path=args.plan)
    write_report(args.output, html_content)

    if args.summary and result.annual and print_header:
        first = result.annual[0]
        last = result.annual[-1]
        print(f"Mode: {result.mode}")
        print(f"Years: {first.year}-{last.year}")
        if result.success_rate is not None:
            print(f"Success rate: {result.success_rate:.1%} ({result.scenario_count} scenarios)")
        print(f"Ending net worth: ${last.net_worth_end:,.0f}")
        print(f"Insolvency years: {len(result.insolvency_years)}")

    print(f"Wrote report to {Path(args.output)}")
    if result.seed is not None:
        print(f"Seed: {result.seed}")


def _plan_mtime_ns(plan_path: str) -> int | None:
    try:
        return Path(plan_path).stat().st_mtime_ns
    except OSError:
        return None


def _run_server_mode(args: argparse.Namespace) -> int:
    if args.validate:
        print("--validate cannot be used with --server", file=sys.stderr)
        return 2
    if args.watch_interval <= 0:
        print("--watch-interval must be > 0", file=sys.stderr)
        return 2

    try:
        plan = load_plan(args.plan)
    except (SchemaError, OSError, ValueError) as exc:
        print(f"Failed to load plan: {exc}", file=sys.stderr)
        return 2

    validation = validate_plan(plan)
    _print_validation(validation.errors, validation.warnings)
    if not validation.is_valid:
        return 1

    _write_report_for_plan(plan, args)

    output_path = Path(args.output).resolve()
    output_dir = str(output_path.parent)
    output_name = output_path.name
    handler = partial(SimpleHTTPRequestHandler, directory=output_dir)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    stop_event = threading.Event()
    state: dict[str, int | None] = {"last_mtime_ns": _plan_mtime_ns(args.plan)}

    def _watch_loop() -> None:
        while not stop_event.wait(args.watch_interval):
            current_mtime_ns = _plan_mtime_ns(args.plan)
            if current_mtime_ns is None or current_mtime_ns == state["last_mtime_ns"]:
                continue
            state["last_mtime_ns"] = current_mtime_ns
            print(f"Detected change in {args.plan}; regenerating report...")
            try:
                plan_update = load_plan(args.plan)
            except (SchemaError, OSError, ValueError) as exc:
                print(f"Failed to load updated plan: {exc}", file=sys.stderr)
                continue
            validation_update = validate_plan(plan_update)
            _print_validation(validation_update.errors, validation_update.warnings)
            if not validation_update.is_valid:
                print("Regeneration failed due to validation errors; serving last successful output.", file=sys.stderr)
                continue
            _write_report_for_plan(plan_update, args, print_header=False)

    watcher = threading.Thread(target=_watch_loop, daemon=True)
    watcher.start()

    print(f"Serving {output_name} at http://{args.host}:{args.port}/{output_name}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        server.server_close()
        watcher.join(timeout=max(args.watch_interval * 2, 0.1))

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.server:
        return _run_server_mode(args)

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

    _write_report_for_plan(plan, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
