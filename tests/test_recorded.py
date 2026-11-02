"""Recorded-answer replay: the key-less demo mode with genuine AI text."""

from pathlib import Path

import pytest

from executive_report.config import LLMSettings
from executive_report.llm import NarrativeError, RecordedWriter, create_writer
from executive_report.pipeline import run_pipeline
from helpers import FakeWriter

FIXTURES = Path(__file__).parent / "fixtures" / "recorded"


def test_create_writer_supports_recorded():
    assert isinstance(create_writer(LLMSettings(provider="recorded")), RecordedWriter)


def test_replays_recorded_answer_with_numbers_matching_the_data(synthetic_dir):
    result = run_pipeline(synthetic_dir, writer=RecordedWriter(FIXTURES))
    assert result.llm.provider == "recorded (handwritten-test-fixture)"
    assert "Agosto fechou com receita de R$ 34.199,26" in result.markdown
    assert result.unverified == []


def test_missing_recording_raises_and_can_fall_back(synthetic_dir, tmp_path):
    writer = RecordedWriter(tmp_path)
    with pytest.raises(NarrativeError, match="No recorded answer for 2018-08"):
        run_pipeline(synthetic_dir, writer=writer)
    result = run_pipeline(synthetic_dir, writer=writer, fallback_to_offline=True)
    assert result.llm.provider == "offline"


def test_save_and_replay_round_trip(synthetic_dir, tmp_path):
    store = RecordedWriter(tmp_path)
    answer = FakeWriter().write({}, [])
    path = store.save("2018-08", answer, recorded_at="2026-11-02")
    assert path.name == "narrative_2018-08.json"
    assert store.available_months() == ["2018-08"]
    replay = run_pipeline(synthetic_dir, writer=store).llm
    assert (replay.provider, replay.model, replay.output_tokens) == (
        "recorded (fake)",
        "fake-model",
        20,
    )
