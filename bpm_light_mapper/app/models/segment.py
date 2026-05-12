from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Segment:
    start: float
    end: float
    bpm: float
    confidence: float
    beats: list[float] = field(default_factory=list)
    confirmed: bool = False
    notes: str = ""

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
