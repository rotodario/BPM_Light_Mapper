from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

import librosa
import numpy as np

from bpm_light_mapper.app.audio.beat_tracker import (
    beat_consistency_confidence,
    detect_beats,
)
from bpm_light_mapper.app.audio.loader import load_audio
from bpm_light_mapper.app.audio.tempo_map import TempoMapParameters, generate_tempo_map
from bpm_light_mapper.app.models.analysis_result import AnalysisResult


@dataclass
class OfflineAnalysisParameters:
    target_sr: int = 22050
    hop_length: int = 512
    start_bpm: float = 120.0
    tightness: float = 100.0
    window_seconds: float = 12.0
    hop_seconds: float = 2.0
    min_bpm_change: float = 3.0
    min_segment_seconds: float = 8.0
    onset_sensitivity: float = 1.0
    bpm_min: float = 60.0
    bpm_max: float = 180.0


def _bpm_candidates(bpm: float, bpm_min: float, bpm_max: float) -> list[float]:
    values = {round(bpm, 2)}
    if bpm / 2 >= bpm_min:
        values.add(round(bpm / 2, 2))
    if bpm * 2 <= bpm_max * 2:
        values.add(round(bpm * 2, 2))
    return sorted(values)


def _estimate_global_bpm_from_beats(
    beat_times: np.ndarray,
    fallback_bpm: float,
    bpm_min: float,
    bpm_max: float,
) -> float:
    if len(beat_times) < 4:
        return float(np.clip(fallback_bpm, bpm_min, bpm_max))
    intervals = np.diff(beat_times)
    if len(intervals) == 0:
        return float(np.clip(fallback_bpm, bpm_min, bpm_max))
    median_interval = float(np.median(intervals))
    if median_interval <= 0:
        return float(np.clip(fallback_bpm, bpm_min, bpm_max))
    bpm = 60.0 / median_interval
    while bpm < bpm_min and bpm > 0:
        bpm *= 2.0
    while bpm > bpm_max:
        bpm /= 2.0
    return float(np.clip(bpm, bpm_min, bpm_max))


def analyze_file(file_path: str, params: OfflineAnalysisParameters, progress_callback=None) -> tuple[dict, AnalysisResult]:
    if progress_callback is not None:
        progress_callback("cargando audio completo...")
    audio = load_audio(file_path, target_sr=params.target_sr)
    waveform = audio["waveform"]
    sample_rate = audio["sample_rate"]

    if progress_callback is not None:
        progress_callback("detectando beats...")
    bpm_global, beat_times, onset_envelope, onset_times = detect_beats(
        waveform,
        sample_rate,
        hop_length=params.hop_length,
        start_bpm=params.start_bpm,
        tightness=params.tightness,
    )
    onset_envelope = onset_envelope * params.onset_sensitivity

    if progress_callback is not None:
        progress_callback("estimando BPM global...")
    bpm_global = _estimate_global_bpm_from_beats(
        beat_times,
        bpm_global,
        params.bpm_min,
        params.bpm_max,
    )

    confidence_global = beat_consistency_confidence(beat_times, bpm_global)
    warnings: list[str] = []
    candidates = _bpm_candidates(bpm_global, params.bpm_min, params.bpm_max)
    if any(abs(candidate - bpm_global) > 15 for candidate in candidates if candidate != bpm_global):
        warnings.append("Posible ambiguedad half-time/double-time. Revisa candidatos alternativos.")

    map_params = TempoMapParameters(
        window_seconds=params.window_seconds,
        hop_seconds=params.hop_seconds,
        min_bpm_change=params.min_bpm_change,
        min_segment_seconds=params.min_segment_seconds,
        onset_sensitivity=params.onset_sensitivity,
        bpm_min=params.bpm_min,
        bpm_max=params.bpm_max,
    )
    if progress_callback is not None:
        progress_callback("segmentando zonas BPM...")
    segments = generate_tempo_map(
        waveform,
        sample_rate,
        beat_times,
        onset_envelope,
        map_params,
        progress_callback=progress_callback,
    )

    result = AnalysisResult(
        file_path=audio["file_path"],
        file_name=audio["file_name"],
        duration=audio["duration"],
        sample_rate=sample_rate,
        channels=audio["channels"],
        bpm_global=bpm_global,
        bpm_candidates=candidates,
        confidence_global=confidence_global,
        beat_times=[float(x) for x in beat_times.tolist()],
        onset_envelope=[float(x) for x in onset_envelope.tolist()],
        onset_times=[float(x) for x in onset_times.tolist()],
        segments=segments,
        parameters=asdict(params),
        warnings=warnings,
        analyzed_at=datetime.now().isoformat(timespec="seconds"),
    )
    return audio, result
