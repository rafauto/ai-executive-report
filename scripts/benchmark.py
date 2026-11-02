"""Time the report generation N times and print Markdown tables for the README.

Usage:
    python scripts/benchmark.py --runs 5 --provider anthropic
    python scripts/benchmark.py --runs 5 --provider offline --data-dir data/sample
"""

from __future__ import annotations

import argparse
import dataclasses
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from executive_report.config import (  # noqa: E402
    BASELINE_AUTOMATION_MIN,
    BASELINE_MANUAL_MIN,
    HUMAN_REVIEW_MIN,
    LLMSettings,
    load_env,
)
from executive_report.pipeline import run_pipeline  # noqa: E402


def main() -> None:
    load_env()
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--provider", default=None)
    p.add_argument("--data-dir", default=None)
    p.add_argument("--month", default=None)
    args = p.parse_args()

    settings = LLMSettings()
    if args.provider:
        settings = dataclasses.replace(settings, provider=args.provider)
    totals, last = [], None
    for i in range(args.runs):
        last = run_pipeline(args.data_dir, args.month, settings)
        totals.append(last.total_seconds)
        print(f"run {i + 1}: {totals[-1]:.2f} s")

    median_s = statistics.median(totals)
    ai_min = median_s / 60 + HUMAN_REVIEW_MIN
    print("\n| Stage | Time (s) |\n|---|---:|")
    for stage, secs in last.timings.items():
        print(f"| {stage} | {secs:.2f} |")
    print(f"| **Total (median of {args.runs})** | **{median_s:.2f}** |")
    print("\n| Process | Time per report | Saved vs. manual |\n|---|---:|---:|")
    print(f"| Manual | {BASELINE_MANUAL_MIN} min | – |")
    saved_auto = 100 * (1 - BASELINE_AUTOMATION_MIN / BASELINE_MANUAL_MIN)
    print(f"| Previous automation | {BASELINE_AUTOMATION_MIN} min | {saved_auto:.0f}% |")
    saved_ai = 100 * (1 - ai_min / BASELINE_MANUAL_MIN)
    label = f"With AI (generation + {HUMAN_REVIEW_MIN} min review)"
    print(f"| {label} | {ai_min:.1f} min | {saved_ai:.0f}% |")
    print(f"\nProvider: {last.llm.provider} · model: {last.llm.model}")


if __name__ == "__main__":
    main()
