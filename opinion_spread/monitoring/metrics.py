"""Simple in-memory metrics recorder for the trading loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class MetricsRecorder:
    counters: Dict[str, float] = field(default_factory=dict)
    last_cycle_duration: float = 0.0

    def increment(self, name: str, value: float = 1.0) -> None:
        self.counters[name] = self.counters.get(name, 0.0) + value

    def observe_cycle_duration(self, duration: float) -> None:
        self.last_cycle_duration = duration
        self.increment("cycle_duration_total", duration)

    def snapshot(self) -> Dict[str, float]:
        data = dict(self.counters)
        data["last_cycle_duration"] = self.last_cycle_duration
        return data

    def merge_counts(self, **counts: float) -> None:
        for key, value in counts.items():
            if value:
                self.increment(key, value)
