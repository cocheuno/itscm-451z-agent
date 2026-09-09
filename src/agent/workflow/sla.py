"""SLA rules (Module 3) and timers (Module 10).

Priority matrix follows the ServiceNow default: priority = f(impact, urgency).
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

PRIORITY_MATRIX = {(1, 1): 1, (1, 2): 2, (2, 1): 2, (2, 2): 3, (1, 3): 3, (3, 1): 3, (2, 3): 4, (3, 2): 4, (3, 3): 5}
# TODO(student, Module 3): response/resolution targets per priority, from your one-page SLA.
TARGETS_MIN = {1: (15, 240), 2: (30, 480), 3: (60, 1440), 4: (240, 2880), 5: (480, 7200)}


def priority(impact: int, urgency: int) -> int:
    return PRIORITY_MATRIX[(impact, urgency)]


@dataclass
class SlaTimer:
    """Injectable clock so tests and demos can compress time (Module 10)."""
    target_min: int
    clock: Callable[[], float] = time.time
    started: float | None = None
    paused_total: float = 0.0
    _pause_at: float | None = None

    def start(self) -> None:
        self.started = self.clock()

    def pause(self) -> None:
        self._pause_at = self.clock()

    def resume(self) -> None:
        if self._pause_at is not None:
            self.paused_total += self.clock() - self._pause_at
            self._pause_at = None

    def elapsed_min(self) -> float:
        if self.started is None:
            return 0.0
        now = self._pause_at if self._pause_at is not None else self.clock()
        return (now - self.started - self.paused_total) / 60

    def breached(self) -> bool:
        return self.elapsed_min() > self.target_min
