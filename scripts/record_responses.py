"""Record real LLM answers for the demo dataset, so the app can replay them without a key.

The answers are generated on the synthetic sample (the dataset the public demo uses)
for the evaluation months and saved to examples/recorded/. Answers whose numbers fail
the guardrail are not saved.

Usage:
    python scripts/record_responses.py --provider anthropic
    python scripts/record_responses.py --provider anthropic --months 2018-08
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from executive_report.cleaning import build_orders_view  # noqa: E402
from executive_report.config import SAMPLE_DATA_DIR, LLMSettings, load_env  # noqa: E402
from executive_report.data_loader import load_olist  # noqa: E402
from executive_report.evaluation import DEFAULT_CASE_MONTHS, build_cases  # noqa: E402
from executive_report.guardrail import unverified_numbers  # noqa: E402
from executive_report.llm import RecordedWriter, create_writer  # noqa: E402


def main() -> int:
    load_env()
    p = argparse.ArgumentParser()
    p.add_argument("--provider", required=True, choices=["anthropic", "openai"])
    p.add_argument("--model", default=None)
    p.add_argument("--months", nargs="+", default=DEFAULT_CASE_MONTHS)
    args = p.parse_args()

    settings = dataclasses.replace(LLMSettings(), provider=args.provider)
    if args.model:
        settings = dataclasses.replace(settings, model=args.model)
    writer, store = create_writer(settings), RecordedWriter()
    view = build_orders_view(load_olist(SAMPLE_DATA_DIR))

    failures = 0
    for case in build_cases(view, args.months):
        result = writer.write(case.data, case.alerts)
        bad = unverified_numbers(result.text, case.data, case.alerts)
        if bad:
            failures += 1
            print(f"{case.month}: not saved, numbers not found in the data: {', '.join(bad)}")
            continue
        path = store.save(case.month, result, recorded_at=date.today().isoformat())
        print(f"{case.month}: saved {path.relative_to(ROOT)} ({result.output_tokens} tokens)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
