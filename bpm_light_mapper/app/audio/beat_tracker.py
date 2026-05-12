from __future__ import annotations

import numpy as np
from scipy.signal import find_peaks


def compute_onset_envelope(
    waveform: np.ndarray,
    sample_rate: int,
    hop_length: int = 512,
    onset_sensitivity: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    frame_length = max(hop_length * 2, 512)
    if len(waveform) < frame_length:
        return np.zeros(0, dtype=np.float32), np.zeros(0, dtype=np.float32)

    samples = np.asarray(waveform, dtype=np.float32)
    squared = np.square(samples, dtype=np.float32)
    cumsum = np.concatenate([[0.0], np.cumsum(squared, dtype=np.float64)])
    starts = np.arange(0, len(samples) - frame_length, hop_length)
    energy = (cumsum[starts + frame_length] - cumsum[starts]) / frame_length
    rms = np.sqrt(np.maximum(energy, 0.0))
    log_rms = np.log1p(rms * 100.0)
    envelope = np.diff(log_rms, prepend=log_rms[0])
    envelope = np.maximum(envelope, 0.0)
    if envelope.size:
        envelope = envelope / max(float(np.max(envelope)), 1e-9)
    envelope = np.maximum(envelope * onset_sensitivity, 0.0).astype(np.float32)
    times = (starts / sample_rate).astype(np.float32)
    return envelope, times


def _estimate_tempo_from_onsets(
    onset_envelope: np.ndarray,
    sample_rate: int,
    hop_length: int,
    bpm_min: float = 60.0,
    bpm_max: float = 180.0,
    fallback_bpm: float = 120.0,
) -> float:
    if len(onset_envelope) < 8 or np.max(onset_envelope) <= 1e-9:
        return fallback_bpm
    novelty = onset_envelope.astype(float) - float(np.mean(onset_envelope))
    corr = np.correlate(novelty, novelty, mode="full")[len(novelty) - 1 :]
    lag_min = max(1, int(np.floor((60.0 / bpm_max) * sample_rate / hop_length)))
    lag_max = min(len(corr) - 1, int(np.ceil((60.0 / bpm_min) * sample_rate / hop_length)))
    if lag_max <= lag_min:
        return fallback_bpm
    local = corr[lag_min : lag_max + 1]
    if len(local) == 0 or np.max(local) <= 1e-9:
        return fallback_bpm
    lag = lag_min + int(np.argmax(local))
    bpm = 60.0 * sample_rate / (hop_length * lag)
    while bpm < bpm_min:
        bpm *= 2.0
    while bpm > bpm_max:
        bpm /= 2.0
    return float(np.clip(bpm, bpm_min, bpm_max))


def _detect_peak_beats(
    onset_envelope: np.ndarray,
    onset_times: np.ndarray,
    sample_rate: int,
    hop_length: int,
    bpm: float,
) -> np.ndarray:
    if len(onset_envelope) == 0 or bpm <= 0:
        return np.zeros(0, dtype=float)
    beat_period_frames = max(1, int(round((60.0 / bpm) * sample_rate / hop_length)))
    min_distance = max(1, int(beat_period_frames * 0.55))
    prominence = max(0.05, float(np.percentile(onset_envelope, 75)) * 0.5)
    peaks, _ = find_peaks(onset_envelope, distance=min_distance, prominence=prominence)
    if len(peaks) < 4:
        peaks, _ = find_peaks(onset_envelope, distance=min_distance)
    return onset_times[peaks].astype(float)


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
    del tightness
    tempo = _estimate_tempo_from_onsets(
        onset_envelope,
        sample_rate,
        hop_length,
        fallback_bpm=start_bpm,
    )
    beat_times = _detect_peak_beats(
        onset_envelope,
        onset_times,
        sample_rate,
        hop_length,
        tempo,
    )
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
