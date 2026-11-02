"""A small, fixed evaluation of narrative quality.

Each case is one month of report data. Every narrative is scored with simple,
deterministic checks, so any provider or prompt change can be compared on the
same cases: `python scripts/run_eval.py --provider anthropic`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from .alerts import evaluate_alerts
from .config import AlertThresholds
from .guardrail import unverified_numbers
from .kpis import build_report_data
from .llm import REQUIRED_SECTIONS, NarrativeWriter

DEFAULT_CASE_MONTHS = ["2018-03", "2018-05", "2018-06", "2018-07", "2018-08"]
MIN_WORDS, MAX_WORDS = 80, 700

# Words the alert analysis must use to show it covered each alert.
ALERT_KEYWORDS = {
    "REVENUE_DROP": ["receita"],
    "ORDERS_DROP": ["pedidos"],
    "LATE_DELIVERIES": ["atras"],
    "HIGH_CANCELLATIONS": ["cancel"],
    "LOW_REVIEW_SCORE": ["nota", "avalia", "satisfa"],
    "NEGATIVE_REVIEWS": ["avalia", "negativ"],
}


@dataclass
class EvalCase:
    month: str
    data: dict
    alerts: list[dict]


def build_cases(
    view: pd.DataFrame,
    months: list[str] | None = None,
    thresholds: AlertThresholds | None = None,
) -> list[EvalCase]:
    thresholds = thresholds or AlertThresholds()
    cases = []
    for month in months or DEFAULT_CASE_MONTHS:
        data = build_report_data(view, pd.Period(month, "M"), thresholds.min_state_orders)
        alerts = [a.to_dict() for a in evaluate_alerts(data, thresholds)]
        cases.append(EvalCase(month, data, alerts))
    return cases


def _section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    rest = text[start + len(heading) :]
    nxt = rest.find("\n## ")
    return rest if nxt < 0 else rest[:nxt]


def _alert_keywords(alert: dict) -> list[str]:
    if alert["code"] == "CATEGORY_DROP":
        return [alert["title"].split("'")[1]]  # the category name
    if alert["code"] == "STATE_LATE_DELIVERIES":
        return [alert["title"].split()[-1]]  # the state code, e.g. RJ
    return ALERT_KEYWORDS.get(alert["code"], [])


def score_narrative(text: str, data: dict, alerts: list[dict]) -> dict[str, bool]:
    """Pass/fail per check. A narrative passes the case when every check is True."""
    analysis = _section(text, "## Análise dos alertas").lower()
    recommendations = _section(text, "## Recomendações")
    n_recommendations = len(re.findall(r"^\s*\d+\.\s", recommendations, flags=re.MULTILINE))
    n_words = len(text.split())
    return {
        "has_all_sections": all(s in text for s in REQUIRED_SECTIONS),
        "no_unverified_numbers": not unverified_numbers(text, data, alerts),
        "covers_every_alert": all(
            any(word.lower() in analysis for word in _alert_keywords(a)) for a in alerts
        ),
        "three_to_five_recommendations": 3 <= n_recommendations <= 5,
        "reasonable_length": MIN_WORDS <= n_words <= MAX_WORDS,
    }


def run_eval(writer: NarrativeWriter, cases: list[EvalCase]) -> list[dict]:
    """Score the writer on every case. Errors count as failed cases."""
    rows = []
    for case in cases:
        try:
            checks = score_narrative(
                writer.write(case.data, case.alerts).text, case.data, case.alerts
            )
            error = None
        except Exception as exc:  # a failed call is a failed case, not a crash
            checks, error = {}, f"{type(exc).__name__}: {exc}"
        rows.append(
            {
                "month": case.month,
                "alerts": len(case.alerts),
                "passed": bool(checks) and all(checks.values()),
                "failed_checks": [name for name, ok in checks.items() if not ok],
                "error": error,
            }
        )
    return rows


def pass_rate(rows: list[dict]) -> float:
    return round(100 * sum(r["passed"] for r in rows) / len(rows), 1) if rows else 0.0
