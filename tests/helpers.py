"""Shared test doubles."""

from executive_report.llm import REQUIRED_SECTIONS, LLMResult

GOOD_ANSWER = "\n".join(f"{s}\nTexto." for s in REQUIRED_SECTIONS)


class FakeWriter:
    """In-memory writer: the integration tests never touch a real SDK."""

    def __init__(self, text: str = GOOD_ANSWER, error: Exception | None = None):
        self.text, self.error, self.calls = text, error, 0

    def write(self, data, alerts):
        self.calls += 1
        if self.error:
            raise self.error
        return LLMResult(self.text, "fake", "fake-model", 10, 20)
