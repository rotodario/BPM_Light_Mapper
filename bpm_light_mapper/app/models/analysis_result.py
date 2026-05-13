from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from bpm_light_mapper.app.models.segment import Segment
from bpm_light_mapper.app.models.tempo_candidate import TempoCandidate


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
    tempo_candidates: list[TempoCandidate] = field(default_factory=list)
    beat_times: list[float] = field(default_factory=list)
    onset_envelope: list[float] = field(default_factory=list)
    onset_times: list[float] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    diagnostic_summary: str = ""
    downbeat_time: Optional[float] = None
    analyzed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["segments"] = [segment.to_dict() for segment in self.segments]
        data["tempo_candidates"] = [candidate.to_dict() for candidate in self.tempo_candidates]
        return data
