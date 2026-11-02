"""Orchestrate the full flow: data -> KPIs -> alerts -> LLM -> report."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .alerts import evaluate_alerts
from .cleaning import build_orders_view, latest_complete_month
from .config import SAMPLE_DATA_DIR, AlertThresholds, LLMSettings, resolve_data_dir
from .data_loader import load_olist
from .kpis import build_report_data
from .llm import LLMResult, generate_narrative, unverified_numbers
from .report import render_report
from .timing import StageTimer


@dataclass
class ReportResult:
    markdown: str
    data: dict
    alerts: list[dict]
    llm: LLMResult
    timings: dict[str, float]
    unverified: list[str] = field(default_factory=list)

    @property
    def month(self) -> str:
        return self.data["reference_month"]

    def metrics(self) -> dict:
        return {
            "reference_month": self.month,
            "stage_seconds": self.timings,
            "total_seconds": round(sum(self.timings.values()), 3),
            "llm": {
                "provider": self.llm.provider,
                "model": self.llm.model,
                "input_tokens": self.llm.input_tokens,
                "output_tokens": self.llm.output_tokens,
            },
            "alerts": len(self.alerts),
            "unverified_numbers": self.unverified,
        }

    def save(self, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        md_path = out_dir / f"report_{self.month}.md"
        md_path.write_text(self.markdown, encoding="utf-8")
        (out_dir / f"metrics_{self.month}.json").write_text(
            json.dumps(self.metrics(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return md_path


def run_pipeline(
    data_dir: str | Path | None = None,
    month: str | None = None,
    settings: LLMSettings | None = None,
    thresholds: AlertThresholds | None = None,
    view: pd.DataFrame | None = None,
) -> ReportResult:
    thresholds = thresholds or AlertThresholds()
    data_path = resolve_data_dir(data_dir)
    timer = StageTimer()

    if view is None:
        with timer.stage("1_load_data"):
            tables = load_olist(data_path)
        with timer.stage("2_clean"):
            view = build_orders_view(tables)

    with timer.stage("3_kpis_and_alerts"):
        period = pd.Period(month, "M") if month else latest_complete_month(view)
        data = build_report_data(view, period, thresholds.min_state_orders)
        alerts = [a.to_dict() for a in evaluate_alerts(data, thresholds)]

    with timer.stage("4_llm_narrative"):
        llm = generate_narrative(data, alerts, settings)

    with timer.stage("5_render_report"):
        unverified = unverified_numbers(llm.text, data, alerts)
        is_sample = Path(data_path).resolve() == SAMPLE_DATA_DIR.resolve()
        source = "amostra sintética (schema Olist)" if is_sample else "Olist / Kaggle"
        markdown = render_report(data, alerts, llm, timer.stages, unverified, source)

    return ReportResult(markdown, data, alerts, llm, dict(timer.stages), unverified)
