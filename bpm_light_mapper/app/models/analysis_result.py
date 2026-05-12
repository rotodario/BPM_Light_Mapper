from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from bpm_light_mapper.app.models.segment import Segment


@dataclass
class AnalysisResult:
    file_path: str
    file_name: str
    duration: float
    sample_rate: int
    channels: int
    bpm_global: float
    bpm_candidates: list[float]
    confidence_global: float
    beat_times: list[float] = field(default_factory=list)
    onset_envelope: list[float] = field(default_factory=list)
    onset_times: list[float] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    analyzed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["segments"] = [segment.to_dict() for segment in self.segments]
        return data
