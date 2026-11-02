"""Smoke test of the Streamlit app, headless. Skipped when Streamlit isn't installed."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_app_generates_offline_report(monkeypatch):
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "LLM_PROVIDER"):
        monkeypatch.delenv(key, raising=False)  # no key -> the app defaults to offline

    at = AppTest.from_file(str(APP), default_timeout=120).run()
    assert not at.exception
    at.button[0].click().run()
    assert not at.exception
    assert any("Relatório Executivo" in md.value for md in at.markdown)
