"""Integration tests: the whole pipeline end to end, with an injected fake writer."""

import json

import pytest

from executive_report.cleaning import build_orders_view
from executive_report.config import LLMSettings
from executive_report.data_loader import load_olist
from executive_report.llm import NarrativeError
from executive_report.pipeline import resolve_month, run_pipeline
from helpers import FakeWriter


def test_end_to_end_offline(synthetic_dir, tmp_path):
    result = run_pipeline(synthetic_dir, settings=LLMSettings(provider="offline"))
    assert result.month == "2018-08"
    assert "# Relatório Executivo · 2018-08" in result.markdown
    assert "## Indicadores principais" in result.markdown
    assert result.unverified == []
    assert set(result.timings) >= {"1_load_data", "4_llm_narrative"}
    assert result.total_seconds == pytest.approx(sum(result.timings.values()), abs=0.01)

    path = result.save(tmp_path)
    assert path.read_text(encoding="utf-8") == result.markdown
    metrics = json.loads((tmp_path / "metrics_2018-08.json").read_text(encoding="utf-8"))
    assert metrics["llm"]["provider"] == "offline"


def test_injected_writer_text_lands_in_report(synthetic_dir):
    writer = FakeWriter()
    result = run_pipeline(synthetic_dir, writer=writer)
    assert writer.calls == 1
    assert "## Recomendações\nTexto." in result.markdown
    assert "tokens: 10 entrada / 20 saída" in result.markdown


def test_invented_number_is_flagged_in_report(synthetic_dir):
    text = FakeWriter().text + "\nO NPS subiu para 99,9%."
    result = run_pipeline(synthetic_dir, writer=FakeWriter(text))
    assert result.unverified == ["99,9%"]
    assert "Verificação automática" in result.markdown


def test_llm_failure_raises_without_fallback(synthetic_dir):
    with pytest.raises(NarrativeError):
        run_pipeline(synthetic_dir, writer=FakeWriter(error=NarrativeError("down")))


def test_llm_failure_falls_back_to_offline(synthetic_dir):
    writer = FakeWriter(error=NarrativeError("provider down"))
    result = run_pipeline(synthetic_dir, writer=writer, fallback_to_offline=True)
    assert result.llm.provider == "offline"
    assert result.fallback_reason == "provider down"


@pytest.fixture(scope="module")
def view(synthetic_dir):
    return build_orders_view(load_olist(synthetic_dir))


@pytest.mark.parametrize("bad", ["2018-8", "08-2018", "2018-13", "abc"])
def test_month_format_is_validated(view, bad):
    with pytest.raises(ValueError, match="YYYY-MM"):
        resolve_month(view, bad)


def test_month_outside_data_is_rejected(view):
    with pytest.raises(ValueError, match="not available"):
        resolve_month(view, "2020-01")
    with pytest.raises(ValueError, match="not available"):
        resolve_month(view, "2017-01")  # first month: nothing to compare with


def test_valid_month_is_accepted(view):
    assert str(resolve_month(view, "2018-06")) == "2018-06"
