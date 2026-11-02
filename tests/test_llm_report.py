"""LLM and report tests. Every API call is mocked: the suite runs fully offline."""

import json
import sys
import types

import pandas as pd
import pytest

from executive_report.alerts import evaluate_alerts
from executive_report.cleaning import build_orders_view
from executive_report.config import LLMSettings
from executive_report.formatting import brl, pct
from executive_report.kpis import build_report_data
from executive_report.llm import (
    REQUIRED_SECTIONS,
    build_user_prompt,
    generate_narrative,
    unverified_numbers,
)
from executive_report.pipeline import run_pipeline

GOOD_ANSWER = "\n".join(f"{s}\nTexto." for s in REQUIRED_SECTIONS)


@pytest.fixture
def report_inputs(tiny_tables):
    view = build_orders_view(tiny_tables)
    data = build_report_data(view, pd.Period("2018-08", "M"), min_state_orders=1)
    return data, [a.to_dict() for a in evaluate_alerts(data)]


def test_brazilian_formatting():
    assert brl(1234.5) == "R$ 1.234,50"
    assert pct(-13.456) == "-13,5%"
    assert pct(2.0, signed=True) == "+2,0%"
    assert pct(None) == "n/d"


def test_offline_narrative_has_all_sections(report_inputs):
    result = generate_narrative(*report_inputs, LLMSettings(provider="offline"))
    assert all(section in result.text for section in REQUIRED_SECTIONS)


def test_prompt_contains_json_payload(report_inputs):
    prompt = build_user_prompt(*report_inputs)
    payload = json.loads(prompt.split("```json\n")[1].split("\n```")[0])
    assert payload["kpis"]["orders"] == 3
    assert "alerts" in payload


def _fake_anthropic(monkeypatch, answer: str, captured: dict):
    class FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            block = types.SimpleNamespace(type="text", text=answer)
            usage = types.SimpleNamespace(input_tokens=1200, output_tokens=450)
            return types.SimpleNamespace(content=[block], usage=usage)

    class FakeClient:
        def __init__(self, api_key=None):
            captured["api_key"] = api_key
            self.messages = FakeMessages()

    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace(Anthropic=FakeClient))


def test_anthropic_provider_is_called_correctly(monkeypatch, report_inputs):
    captured: dict = {}
    _fake_anthropic(monkeypatch, GOOD_ANSWER, captured)
    settings = LLMSettings(provider="anthropic", model="test-model", api_key="sk-test")
    result = generate_narrative(*report_inputs, settings)
    assert result.provider == "anthropic"
    assert result.output_tokens == 450
    assert captured["model"] == "test-model"
    assert captured["api_key"] == "sk-test"
    assert "APENAS os números" in captured["system"]


def test_openai_compatible_provider(monkeypatch, report_inputs):
    captured: dict = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            message = types.SimpleNamespace(content=GOOD_ANSWER)
            usage = types.SimpleNamespace(prompt_tokens=900, completion_tokens=300)
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=message)], usage=usage
            )

    class FakeOpenAI:
        def __init__(self, api_key=None, base_url=None):
            captured["base_url"] = base_url
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
    result = generate_narrative(*report_inputs, LLMSettings(provider="openai", model="llama"))
    assert result.input_tokens == 900
    assert captured["base_url"] == "https://api.groq.com/openai/v1"
    assert captured["messages"][0]["role"] == "system"


def test_malformed_llm_answer_is_rejected(monkeypatch, report_inputs):
    _fake_anthropic(monkeypatch, "Some text without the sections.", {})
    with pytest.raises(ValueError, match="missing sections"):
        generate_narrative(*report_inputs, LLMSettings(provider="anthropic"))


def test_invalid_provider(report_inputs):
    with pytest.raises(ValueError, match="Invalid LLM_PROVIDER"):
        generate_narrative(*report_inputs, LLMSettings(provider="xpto"))


def test_guardrail_flags_invented_numbers(report_inputs):
    data, alerts = report_inputs
    text = (
        f"Receita de {brl(data['kpis']['revenue'])} e cancelamento de 25,0%. Mas o NPS foi 87,3%."
    )
    assert unverified_numbers(text, data, alerts) == ["87,3%"]


def test_pipeline_end_to_end_offline(synthetic_dir, tmp_path):
    result = run_pipeline(synthetic_dir, settings=LLMSettings(provider="offline"))
    assert result.month == "2018-08"
    assert "# Relatório Executivo · 2018-08" in result.markdown
    assert "## Indicadores principais" in result.markdown
    assert result.unverified == []
    assert set(result.timings) >= {"1_load_data", "4_llm_narrative"}

    path = result.save(tmp_path)
    assert path.read_text(encoding="utf-8") == result.markdown
    metrics = json.loads((tmp_path / "metrics_2018-08.json").read_text(encoding="utf-8"))
    assert metrics["llm"]["provider"] == "offline"
