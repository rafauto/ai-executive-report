"""Evaluate narrative quality on a fixed set of months and print a Markdown table.

Usage:
    python scripts/run_eval.py --provider offline           # harness check, no cost
    python scripts/run_eval.py --provider anthropic         # real LLM (~5 calls)
    python scripts/run_eval.py --provider anthropic --data-dir data/raw
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from executive_report.cleaning import build_orders_view  # noqa: E402
from executive_report.config import LLMSettings, load_env, resolve_data_dir  # noqa: E402
from executive_report.data_loader import load_olist  # noqa: E402
from executive_report.evaluation import build_cases, pass_rate, run_eval  # noqa: E402
from executive_report.llm import create_writer  # noqa: E402


def main() -> int:
    load_env()
    p = argparse.ArgumentParser()
    p.add_argument("--provider", default=None)
    p.add_argument("--data-dir", default=None)
    p.add_argument("--min-pass-rate", type=float, default=80.0, help="Target: exit 1 below this %%")
    args = p.parse_args()

    settings = LLMSettings()
    if args.provider:
        settings = dataclasses.replace(settings, provider=args.provider)

    view = build_orders_view(load_olist(resolve_data_dir(args.data_dir)))
    rows = run_eval(create_writer(settings), build_cases(view))

    print("| Month | Alerts | Passed | Failed checks |\n|---|---:|:---:|---|")
    for r in rows:
        failed = r["error"] or ", ".join(r["failed_checks"]) or "–"
        status = "✅" if r["passed"] else "❌"
        print(f"| {r['month']} | {r['alerts']} | {status} | {failed} |")
    rate = pass_rate(rows)
    model = settings.resolved_model or "rules"
    print(f"\nPass rate: {rate}% · provider: {settings.provider} ({model})")
    return 0 if rate >= args.min_pass_rate else 1


if __name__ == "__main__":
    raise SystemExit(main())
