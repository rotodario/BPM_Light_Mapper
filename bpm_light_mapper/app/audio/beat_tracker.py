from __future__ import annotations

import numpy as np
import librosa


def compute_onset_envelope(
    waveform: np.ndarray,
    sample_rate: int,
    hop_length: int = 512,
    onset_sensitivity: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    envelope = librosa.onset.onset_strength(
        y=waveform,
        sr=sample_rate,
        hop_length=hop_length,
        aggregate=np.median,
    )
    envelope = np.maximum(envelope * onset_sensitivity, 0.0)
    times = librosa.times_like(envelope, sr=sample_rate, hop_length=hop_length)
    return envelope, times


def detect_beats(
    waveform: np.ndarray,
    sample_rate: int,
    hop_length: int = 512,
    start_bpm: float = 120.0,
    tightness: float = 100.0,
) -> tuple[float, np.ndarray, np.ndarray, np.ndarray]:
    onset_envelope, onset_times = compute_onset_envelope(
        waveform,
        sample_rate,
        hop_length=hop_length,
    )
    tempo, beat_frames = librosa.beat.beat_track(
        y=waveform,
        sr=sample_rate,
        onset_envelope=onset_envelope,
        hop_length=hop_length,
        start_bpm=start_bpm,
        tightness=tightness,
        units="frames",
    )
    beat_times = librosa.frames_to_time(beat_frames, sr=sample_rate, hop_length=hop_length)
    return float(tempo), beat_times, onset_envelope, onset_times


def beat_consistency_confidence(beat_times: np.ndarray, target_bpm: float) -> float:
    if len(beat_times) < 4 or target_bpm <= 0:
        return 0.0
    intervals = np.diff(beat_times)
    expected = 60.0 / target_bpm
    median_error = np.median(np.abs(intervals - expected))
    jitter_score = max(0.0, 1.0 - (median_error / max(expected, 1e-6)))
    spread_penalty = min(1.0, np.std(intervals) / max(expected, 1e-6))
    return float(np.clip(jitter_score * (1.0 - 0.5 * spread_penalty), 0.0, 1.0))
