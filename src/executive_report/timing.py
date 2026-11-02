"""Per-stage stopwatch used to measure the time saved."""

from __future__ import annotations

import time
from contextlib import contextmanager


class StageTimer:
    def __init__(self) -> None:
        self.stages: dict[str, float] = {}

    @contextmanager
    def stage(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            self.stages[name] = round(time.perf_counter() - start, 3)

    @property
    def total_seconds(self) -> float:
        return round(sum(self.stages.values()), 3)
