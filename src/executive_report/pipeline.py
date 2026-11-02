"""Orchestrate the full flow: data -> KPIs -> alerts -> LLM -> report."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .alerts import evaluate_alerts
from .cleaning import build_orders_view, latest_complete_month
from .config import SAMPLE_DATA_DIR, AlertThresholds, LLMSettings, resolve_data_dir
from .data_loader import load_olist
from .guardrail import unverified_numbers
from .kpis import build_report_data
from .llm import (
    LLMResult,
    NarrativeError,
    NarrativeWriter,
    OfflineWriter,
    create_writer,
    generate_narrative,
)
from .report import render_report
from .timing import StageTimer

logger = logging.getLogger(__name__)

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@dataclass
class ReportResult:
    markdown: str
    data: dict
    alerts: list[dict]
    llm: LLMResult
    timings: dict[str, float]
    unverified: list[str] = field(default_factory=list)
    fallback_reason: str | None = None  # set when the LLM failed and offline text was used

    @property
    def month(self) -> str:
        return self.data["reference_month"]

    @property
    def total_seconds(self) -> float:
        return round(sum(self.timings.values()), 3)

    def metrics(self) -> dict:
        return {
            "reference_month": self.month,
            "stage_seconds": self.timings,
            "total_seconds": self.total_seconds,
            "llm": {
                "provider": self.llm.provider,
                "model": self.llm.model,
                "input_tokens": self.llm.input_tokens,
                "output_tokens": self.llm.output_tokens,
            },
            "alerts": len(self.alerts),
            "unverified_numbers": self.unverified,
            "fallback_reason": self.fallback_reason,
        }

    def save(self, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        md_path = out_dir / f"report_{self.month}.md"
        md_path.write_text(self.markdown, encoding="utf-8")
        (out_dir / f"metrics_{self.month}.json").write_text(
            json.dumps(self.metrics(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return md_path


def resolve_month(view: pd.DataFrame, month: str | None) -> pd.Period:
    """Validate a YYYY-MM input against the months available in the data."""
    if month is None:
        return latest_complete_month(view)
    if not _MONTH_RE.match(month):
        raise ValueError(f"Invalid month {month!r}: use the YYYY-MM format, e.g. 2018-08.")
    period = pd.Period(month, "M")
    available = sorted(view["month"].unique())
    if period not in available[1:]:  # the first month has no previous month to compare
        raise ValueError(
            f"Month {month} is not available. Choose between {available[1]} and {available[-1]}."
        )
    return period


def run_pipeline(
    data_dir: str | Path | None = None,
    month: str | None = None,
    settings: LLMSettings | None = None,
    thresholds: AlertThresholds | None = None,
    view: pd.DataFrame | None = None,
    writer: NarrativeWriter | None = None,
    fallback_to_offline: bool = False,
) -> ReportResult:
    """Build the report. `writer` can be injected (tests); otherwise it comes from `settings`.

    With `fallback_to_offline=True` an LLM failure produces the rule-based narrative
    instead of an error, so the app keeps working when the provider is down.
    """
    thresholds = thresholds or AlertThresholds()
    writer = writer or create_writer(settings or LLMSettings())
    data_path = resolve_data_dir(data_dir)
    timer = StageTimer()

    if view is None:
        with timer.stage("1_load_data"):
            tables = load_olist(data_path)
        with timer.stage("2_clean"):
            view = build_orders_view(tables)

    with timer.stage("3_kpis_and_alerts"):
        period = resolve_month(view, month)
        data = build_report_data(view, period, thresholds.min_state_orders)
        alerts = [a.to_dict() for a in evaluate_alerts(data, thresholds)]

    fallback_reason = None
    with timer.stage("4_llm_narrative"):
        try:
            llm = generate_narrative(data, alerts, writer)
        except NarrativeError as exc:
            if not fallback_to_offline:
                raise
            logger.warning("Falling back to the offline narrative: %s", exc)
            fallback_reason = str(exc)
            llm = OfflineWriter().write(data, alerts)

    with timer.stage("5_render_report"):
        unverified = unverified_numbers(llm.text, data, alerts)
        is_sample = Path(data_path).resolve() == SAMPLE_DATA_DIR.resolve()
        source = "amostra sintética (schema Olist)" if is_sample else "Olist / Kaggle"
        markdown = render_report(data, alerts, llm, timer.stages, unverified, source)

    logger.info("Report %s generated in %.2f s", period, sum(timer.stages.values()))
    return ReportResult(
        markdown, data, alerts, llm, dict(timer.stages), unverified, fallback_reason
    )
