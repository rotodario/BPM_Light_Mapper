from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class TempoCandidate:
    label: str
    bpm: float
    beat_interval_ms: float
    grid_alignment_score: float
    onset_alignment_score: float
    accent_score: float
    confidence: float
    in_configured_range: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
