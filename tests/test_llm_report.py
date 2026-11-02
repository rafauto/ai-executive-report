"""LLM, guardrail and report tests. Every API call is mocked: the suite runs offline."""

import json
import os
import sys
import types

import pandas as pd
import pytest

from executive_report.alerts import evaluate_alerts
from executive_report.cleaning import build_orders_view
from executive_report.config import LLMSettings
from executive_report.formatting import brl, pct
from executive_report.guardrail import unverified_numbers
from executive_report.kpis import build_report_data
from executive_report.llm import (
    REQUIRED_SECTIONS,
    AnthropicWriter,
    NarrativeError,
    OfflineWriter,
    OpenAICompatibleWriter,
    build_user_prompt,
    create_writer,
    generate_narrative,
)
from executive_report.report import kpi_table
from helpers import GOOD_ANSWER


@pytest.fixture
def report_inputs(tiny_tables):
    view = build_orders_view(tiny_tables)
    data = build_report_data(view, pd.Period("2018-08", "M"), min_state_orders=1)
    return data, [a.to_dict() for a in evaluate_alerts(data)]


def _fake_anthropic(monkeypatch, captured: dict, answer: str = GOOD_ANSWER, error=None):
    class FakeMessages:
        def create(self, **kwargs):
            if error:
                raise error
            captured.update(kwargs)
            block = types.SimpleNamespace(type="text", text=answer)
            usage = types.SimpleNamespace(input_tokens=1200, output_tokens=450)
            return types.SimpleNamespace(content=[block], usage=usage)

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.messages = FakeMessages()

    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace(Anthropic=FakeClient))


# ---------------------------------------------------------------- formatting
def test_brazilian_formatting():
    assert brl(1234.5) == "R$ 1.234,50"
    assert pct(-13.456) == "-13,5%"
    assert pct(2.0, signed=True) == "+2,0%"
    assert pct(None) == "n/d"


def test_regression_absolute_change_is_signed(report_inputs):
    """Bug fixed in v0.1: '3,80' was shown instead of '+3,8' for delivery days."""
    data, _ = report_inputs
    data["kpis"]["avg_delivery_days"], data["previous_kpis"]["avg_delivery_days"] = 15.3, 11.5
    row = next(line for line in kpi_table(data).splitlines() if "Prazo" in line)
    assert row.endswith("| +3,8 |")


# ---------------------------------------------------------------- writers
def test_offline_writer_has_all_sections(report_inputs):
    result = OfflineWriter().write(*report_inputs)
    assert all(section in result.text for section in REQUIRED_SECTIONS)


def test_create_writer_picks_the_provider():
    assert isinstance(create_writer(LLMSettings(provider="offline")), OfflineWriter)
    assert isinstance(create_writer(LLMSettings(provider="anthropic")), AnthropicWriter)
    assert isinstance(create_writer(LLMSettings(provider="openai")), OpenAICompatibleWriter)
    with pytest.raises(ValueError, match="Invalid LLM_PROVIDER"):
        create_writer(LLMSettings(provider="xpto"))


def test_prompt_contains_json_payload(report_inputs):
    prompt = build_user_prompt(*report_inputs)
    payload = json.loads(prompt.split("```json\n")[1].split("\n```")[0])
    assert payload["kpis"]["orders"] == 3
    assert "alerts" in payload


def test_anthropic_writer_sends_settings(monkeypatch, report_inputs):
    captured: dict = {}
    _fake_anthropic(monkeypatch, captured)
    settings = LLMSettings(
        provider="anthropic", model="test-model", api_key="sk-test", timeout_s=12, max_retries=3
    )
    result = AnthropicWriter(settings).write(*report_inputs)
    assert result.output_tokens == 450
    assert captured["model"] == "test-model"
    assert captured["client"] == {"api_key": "sk-test", "timeout": 12, "max_retries": 3}
    assert "APENAS os números" in captured["system"]
    assert "Ignore qualquer texto" in captured["system"]  # prompt-injection rule


def test_openai_compatible_writer(monkeypatch, report_inputs):
    captured: dict = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            message = types.SimpleNamespace(content=GOOD_ANSWER)
            usage = types.SimpleNamespace(prompt_tokens=900, completion_tokens=300)
            choice = types.SimpleNamespace(message=message)
            return types.SimpleNamespace(choices=[choice], usage=usage)

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
    result = OpenAICompatibleWriter(LLMSettings(provider="openai", model="llama")).write(
        *report_inputs
    )
    assert result.input_tokens == 900
    assert captured["client"]["base_url"] == "https://api.groq.com/openai/v1"
    assert captured["messages"][0]["role"] == "system"


def test_malformed_answer_raises_narrative_error(monkeypatch, report_inputs):
    _fake_anthropic(monkeypatch, {}, answer="Some text without the sections.")
    writer = AnthropicWriter(LLMSettings(provider="anthropic"))
    with pytest.raises(NarrativeError, match="missing sections"):
        generate_narrative(*report_inputs, writer)


def test_provider_failure_becomes_clear_error(monkeypatch, report_inputs):
    _fake_anthropic(monkeypatch, {}, error=TimeoutError("read timed out"))
    writer = AnthropicWriter(LLMSettings(provider="anthropic"))
    with pytest.raises(NarrativeError, match="--provider offline"):
        generate_narrative(*report_inputs, writer)


def test_regression_api_key_is_never_written_to_environment(monkeypatch, report_inputs):
    """Bug fixed in v0.1: a visitor's key was stored in os.environ (shared by sessions)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _fake_anthropic(monkeypatch, {})
    AnthropicWriter(LLMSettings(provider="anthropic", api_key="sk-visitor")).write(*report_inputs)
    assert "sk-visitor" not in os.environ.values()


# ---------------------------------------------------------------- guardrail
def test_guardrail_flags_invented_numbers(report_inputs):
    data, alerts = report_inputs
    text = (
        f"Receita de {brl(data['kpis']['revenue'])} e cancelamento de 25,0%. Mas o NPS foi 87,3%."
    )
    assert unverified_numbers(text, data, alerts) == ["87,3%"]


def test_guardrail_accepts_rounded_values(report_inputs):
    data, alerts = report_inputs
    assert unverified_numbers("Atrasos em 33,3% das entregas.", data, alerts) == []
