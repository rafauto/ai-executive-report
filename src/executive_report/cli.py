"""Command line: `python -m executive_report` or `executive-report`."""

from __future__ import annotations

import argparse
import dataclasses
import logging
import sys
from pathlib import Path

from .config import REPORTS_DIR, LLMSettings, load_env


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="executive-report",
        description="Generate the monthly executive report for the Olist dataset with AI.",
    )
    p.add_argument(
        "--data-dir", help="Folder with the Olist CSVs (default: data/raw, else data/sample)"
    )
    p.add_argument("--month", help="Reference month YYYY-MM (default: latest complete month)")
    p.add_argument(
        "--provider",
        choices=["anthropic", "openai", "offline"],
        help="LLM provider (default: LLM_PROVIDER env var or anthropic)",
    )
    p.add_argument("--model", help="LLM model (default: LLM_MODEL env var)")
    p.add_argument(
        "--out", type=Path, default=REPORTS_DIR, help="Output folder (default: reports/)"
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Show detailed logs")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_env()
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    from .pipeline import run_pipeline  # import pandas only after --help

    settings = LLMSettings()
    if args.provider:
        settings = dataclasses.replace(settings, provider=args.provider)
    if args.model:
        settings = dataclasses.replace(settings, model=args.model)

    try:
        result = run_pipeline(args.data_dir, args.month, settings)
    except Exception as exc:  # friendly message on the command line
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    path = result.save(args.out)
    print(f"Report saved to {path}")
    print(f"Alerts: {len(result.alerts)} · Total time: {result.total_seconds:.1f} s")
    for stage, secs in result.timings.items():
        print(f"  {stage:<20} {secs:>7.2f} s")
    if result.unverified:
        print(f"Warning: numbers to double-check in the AI text: {', '.join(result.unverified)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
